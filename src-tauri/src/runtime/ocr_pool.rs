use super::window_lane::{ExecutionControl, WindowLaneError};
use std::{
    error::Error,
    fmt,
    panic::{catch_unwind, AssertUnwindSafe},
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        mpsc::{self, Receiver, RecvTimeoutError, SyncSender, TrySendError},
        Arc, Mutex,
    },
    thread::{self, JoinHandle},
    time::Duration,
};

pub const DEFAULT_OCR_WORKERS: usize = 2;
pub const DEFAULT_OCR_QUEUE_CAPACITY: usize = 8;
const CONTROL_POLL_INTERVAL: Duration = Duration::from_millis(10);

type OcrTask = Box<dyn FnOnce() -> Result<String, String> + Send + 'static>;
type OcrResponse = Result<String, OcrPoolError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OcrJobStage {
    Queued,
    Running,
}

impl fmt::Display for OcrJobStage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Queued => write!(f, "queued"),
            Self::Running => write!(f, "running"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OcrPoolError {
    Cancelled { stage: OcrJobStage },
    DeadlineExceeded { stage: OcrJobStage },
    QueueFull,
    WorkerUnavailable(String),
    BackendFailed(String),
}

impl fmt::Display for OcrPoolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Cancelled { stage } => write!(f, "OCR job was cancelled while {stage}"),
            Self::DeadlineExceeded { stage } => {
                write!(f, "OCR job exceeded its deadline while {stage}")
            }
            Self::QueueFull => write!(f, "OCR worker queue is full"),
            Self::WorkerUnavailable(detail) => write!(f, "OCR worker unavailable: {detail}"),
            Self::BackendFailed(detail) => write!(f, "OCR backend failed: {detail}"),
        }
    }
}

impl Error for OcrPoolError {}

struct OcrJob {
    control: ExecutionControl,
    started: Arc<AtomicBool>,
    task: OcrTask,
    response: SyncSender<OcrResponse>,
}

struct OcrWorkerPoolInner {
    sender: Mutex<Option<SyncSender<OcrJob>>>,
    shared: Arc<OcrWorkerShared>,
    workers: Mutex<Vec<JoinHandle<()>>>,
}

struct OcrWorkerShared {
    receiver: Arc<Mutex<Receiver<OcrJob>>>,
    queued_jobs: AtomicUsize,
    active_jobs: AtomicUsize,
}

impl Drop for OcrWorkerPoolInner {
    fn drop(&mut self) {
        if let Ok(sender) = self.sender.get_mut() {
            sender.take();
        }
        if let Ok(workers) = self.workers.get_mut() {
            for worker in workers.drain(..) {
                let _ = worker.join();
            }
        }
    }
}

#[derive(Clone)]
pub struct OcrWorkerPool {
    inner: Arc<OcrWorkerPoolInner>,
}

impl Default for OcrWorkerPool {
    fn default() -> Self {
        Self::new(DEFAULT_OCR_WORKERS, DEFAULT_OCR_QUEUE_CAPACITY)
            .expect("default OCR worker pool configuration is valid")
    }
}

impl OcrWorkerPool {
    pub fn new(worker_count: usize, queue_capacity: usize) -> Result<Self, OcrPoolError> {
        if worker_count == 0 || queue_capacity == 0 {
            return Err(OcrPoolError::WorkerUnavailable(
                "worker count and queue capacity must be greater than zero".to_string(),
            ));
        }
        let (sender, receiver) = mpsc::sync_channel(queue_capacity);
        let shared = Arc::new(OcrWorkerShared {
            receiver: Arc::new(Mutex::new(receiver)),
            queued_jobs: AtomicUsize::new(0),
            active_jobs: AtomicUsize::new(0),
        });
        let inner = Arc::new(OcrWorkerPoolInner {
            sender: Mutex::new(Some(sender)),
            shared: Arc::clone(&shared),
            workers: Mutex::new(Vec::with_capacity(worker_count)),
        });

        for index in 0..worker_count {
            let worker_shared = Arc::clone(&shared);
            let handle = thread::Builder::new()
                .name(format!("mhxy-ocr-worker-{index}"))
                .spawn(move || worker_loop(worker_shared))
                .map_err(|error| OcrPoolError::WorkerUnavailable(error.to_string()))?;
            inner
                .workers
                .lock()
                .map_err(|_| {
                    OcrPoolError::WorkerUnavailable("worker handle lock poisoned".to_string())
                })?
                .push(handle);
        }
        Ok(Self { inner })
    }

    pub fn execute(
        &self,
        control: &ExecutionControl,
        task: impl FnOnce() -> Result<String, String> + Send + 'static,
    ) -> Result<String, OcrPoolError> {
        control
            .check_typed()
            .map_err(|error| map_control_error(error, OcrJobStage::Queued))?;
        let started = Arc::new(AtomicBool::new(false));
        let (response, result) = mpsc::sync_channel(1);
        let job = OcrJob {
            control: control.clone(),
            started: Arc::clone(&started),
            task: Box::new(task),
            response,
        };
        let sender = self
            .inner
            .sender
            .lock()
            .map_err(|_| OcrPoolError::WorkerUnavailable("queue lock poisoned".to_string()))?
            .clone()
            .ok_or_else(|| OcrPoolError::WorkerUnavailable("queue is closed".to_string()))?;

        self.inner.shared.queued_jobs.fetch_add(1, Ordering::SeqCst);
        match sender.try_send(job) {
            Ok(()) => {}
            Err(TrySendError::Full(_)) => {
                self.inner.shared.queued_jobs.fetch_sub(1, Ordering::SeqCst);
                return Err(OcrPoolError::QueueFull);
            }
            Err(TrySendError::Disconnected(_)) => {
                self.inner.shared.queued_jobs.fetch_sub(1, Ordering::SeqCst);
                return Err(OcrPoolError::WorkerUnavailable(
                    "all OCR workers disconnected".to_string(),
                ));
            }
        }

        loop {
            let wait = control
                .remaining()
                .map(|remaining| remaining.min(CONTROL_POLL_INTERVAL))
                .unwrap_or(Duration::ZERO);
            match result.recv_timeout(wait) {
                Ok(worker_result) => {
                    let stage = job_stage(&started);
                    control
                        .check_typed()
                        .map_err(|error| map_control_error(error, stage))?;
                    return worker_result;
                }
                Err(RecvTimeoutError::Timeout) => {
                    let stage = job_stage(&started);
                    control
                        .check_typed()
                        .map_err(|error| map_control_error(error, stage))?;
                }
                Err(RecvTimeoutError::Disconnected) => {
                    return Err(OcrPoolError::WorkerUnavailable(
                        "OCR worker dropped the result".to_string(),
                    ));
                }
            }
        }
    }

    #[cfg(test)]
    fn queued_jobs(&self) -> usize {
        self.inner.shared.queued_jobs.load(Ordering::SeqCst)
    }

    #[cfg(test)]
    fn active_jobs(&self) -> usize {
        self.inner.shared.active_jobs.load(Ordering::SeqCst)
    }
}

fn worker_loop(shared: Arc<OcrWorkerShared>) {
    let initialized = initialize_worker_runtime();
    loop {
        let job = {
            let receiver = match shared.receiver.lock() {
                Ok(receiver) => receiver,
                Err(_) => return,
            };
            match receiver.recv() {
                Ok(job) => job,
                Err(_) => break,
            }
        };
        shared.queued_jobs.fetch_sub(1, Ordering::SeqCst);
        if let Err(error) = job.control.check_typed() {
            let _ = job
                .response
                .send(Err(map_control_error(error, OcrJobStage::Queued)));
            continue;
        }
        if let Err(detail) = &initialized {
            let _ = job
                .response
                .send(Err(OcrPoolError::WorkerUnavailable(detail.clone())));
            continue;
        }

        job.started.store(true, Ordering::SeqCst);
        shared.active_jobs.fetch_add(1, Ordering::SeqCst);
        let response = match catch_unwind(AssertUnwindSafe(job.task)) {
            Ok(Ok(text)) => Ok(text),
            Ok(Err(detail)) => Err(OcrPoolError::BackendFailed(detail)),
            Err(_) => Err(OcrPoolError::WorkerUnavailable(
                "OCR backend panicked".to_string(),
            )),
        };
        shared.active_jobs.fetch_sub(1, Ordering::SeqCst);
        let response = match job.control.check_typed() {
            Ok(()) => response,
            Err(error) => Err(map_control_error(error, OcrJobStage::Running)),
        };
        let _ = job.response.send(response);
    }
    uninitialize_worker_runtime(initialized.is_ok());
}

fn job_stage(started: &AtomicBool) -> OcrJobStage {
    if started.load(Ordering::SeqCst) {
        OcrJobStage::Running
    } else {
        OcrJobStage::Queued
    }
}

fn map_control_error(error: WindowLaneError, stage: OcrJobStage) -> OcrPoolError {
    match error {
        WindowLaneError::Cancelled { .. } => OcrPoolError::Cancelled { stage },
        WindowLaneError::DeadlineExceeded { .. } => OcrPoolError::DeadlineExceeded { stage },
        WindowLaneError::SynchronizationPoisoned => {
            OcrPoolError::WorkerUnavailable(WindowLaneError::SynchronizationPoisoned.to_string())
        }
    }
}

#[cfg(all(windows, not(test)))]
fn initialize_worker_runtime() -> Result<(), String> {
    use windows::Win32::System::WinRT::{RoInitialize, RO_INIT_MULTITHREADED};
    unsafe { RoInitialize(RO_INIT_MULTITHREADED) }.map_err(|error| error.to_string())
}

#[cfg(not(all(windows, not(test))))]
fn initialize_worker_runtime() -> Result<(), String> {
    Ok(())
}

#[cfg(all(windows, not(test)))]
fn uninitialize_worker_runtime(initialized: bool) {
    if initialized {
        use windows::Win32::System::WinRT::RoUninitialize;
        unsafe { RoUninitialize() };
    }
}

#[cfg(not(all(windows, not(test))))]
fn uninitialize_worker_runtime(_initialized: bool) {}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::runtime::window_lane::{ExecutionContextInput, WindowLaneRegistry};
    use std::sync::{
        atomic::{AtomicUsize, Ordering},
        Condvar,
    };
    use std::time::Instant;

    fn control(
        registry: &WindowLaneRegistry,
        hwnd: isize,
        session: &str,
        deadline_ms: u64,
    ) -> (super::super::window_lane::WindowLaneGuard, ExecutionControl) {
        let guard = registry
            .acquire(
                hwnd,
                ExecutionContextInput {
                    session_id: session.to_string(),
                    step_id: format!("step-{session}"),
                    deadline_ms,
                    cancel_token_id: format!("cancel-{session}"),
                },
            )
            .unwrap();
        let control = guard.control();
        (guard, control)
    }

    fn release_gate() -> Arc<(Mutex<bool>, Condvar)> {
        Arc::new((Mutex::new(false), Condvar::new()))
    }

    fn wait_gate(gate: &Arc<(Mutex<bool>, Condvar)>) {
        let (lock, changed) = &**gate;
        let mut released = lock.lock().unwrap();
        while !*released {
            released = changed.wait(released).unwrap();
        }
    }

    fn open_gate(gate: &Arc<(Mutex<bool>, Condvar)>) {
        let (lock, changed) = &**gate;
        *lock.lock().unwrap() = true;
        changed.notify_all();
    }

    fn wait_until(predicate: impl Fn() -> bool) {
        let deadline = Instant::now() + Duration::from_secs(2);
        while !predicate() {
            assert!(Instant::now() < deadline, "condition did not become true");
            thread::sleep(Duration::from_millis(5));
        }
    }

    #[test]
    fn worker_count_stays_bounded() {
        let _pool = OcrWorkerPool::default();
        assert_eq!(DEFAULT_OCR_WORKERS, 2);
        assert_eq!(DEFAULT_OCR_QUEUE_CAPACITY, 8);
    }

    #[test]
    fn workers_execute_in_parallel() {
        let pool = OcrWorkerPool::new(2, 8).unwrap();
        let registry = WindowLaneRegistry::new();
        let gate = release_gate();
        let active = Arc::new(AtomicUsize::new(0));
        let mut handles = Vec::new();
        let mut guards = Vec::new();
        for index in 0..2 {
            let (guard, control) = control(&registry, 100 + index, &format!("s{index}"), 5_000);
            guards.push(guard);
            let pool = pool.clone();
            let gate = Arc::clone(&gate);
            let active = Arc::clone(&active);
            handles.push(thread::spawn(move || {
                pool.execute(&control, move || {
                    active.fetch_add(1, Ordering::SeqCst);
                    wait_gate(&gate);
                    Ok("ok".to_string())
                })
            }));
        }
        wait_until(|| active.load(Ordering::SeqCst) == 2);
        assert_eq!(pool.active_jobs(), 2);
        open_gate(&gate);
        for handle in handles {
            assert_eq!(handle.join().unwrap().unwrap(), "ok");
        }
        drop(guards);
    }

    #[test]
    fn queue_full_returns_immediately() {
        let pool = OcrWorkerPool::new(2, 8).unwrap();
        let registry = WindowLaneRegistry::new();
        let gate = release_gate();
        let mut handles = Vec::new();
        let mut guards = Vec::new();
        for index in 0..10 {
            let (guard, control) = control(&registry, 200 + index, &format!("q{index}"), 5_000);
            guards.push(guard);
            let pool = pool.clone();
            let gate = Arc::clone(&gate);
            handles.push(thread::spawn(move || {
                pool.execute(&control, move || {
                    wait_gate(&gate);
                    Ok("ok".to_string())
                })
            }));
        }
        wait_until(|| pool.active_jobs() == 2 && pool.queued_jobs() == 8);
        let (_guard, overflow) = control(&registry, 999, "overflow", 5_000);
        let started = Instant::now();
        assert_eq!(
            pool.execute(&overflow, || Ok("never".to_string())),
            Err(OcrPoolError::QueueFull)
        );
        assert!(started.elapsed() < Duration::from_millis(100));
        open_gate(&gate);
        for handle in handles {
            handle.join().unwrap().unwrap();
        }
        drop(guards);
    }

    #[test]
    fn queued_cancel_never_calls_backend() {
        queued_control_failure_never_calls_backend(true);
    }

    #[test]
    fn queued_deadline_never_calls_backend() {
        queued_control_failure_never_calls_backend(false);
    }

    fn queued_control_failure_never_calls_backend(cancel: bool) {
        let pool = OcrWorkerPool::new(2, 8).unwrap();
        let registry = WindowLaneRegistry::new();
        let gate = release_gate();
        let mut blockers = Vec::new();
        let mut blocker_guards = Vec::new();
        for index in 0..2 {
            let (guard, control) = control(&registry, 300 + index, &format!("block{index}"), 5_000);
            blocker_guards.push(guard);
            let pool = pool.clone();
            let gate = Arc::clone(&gate);
            blockers.push(thread::spawn(move || {
                pool.execute(&control, move || {
                    wait_gate(&gate);
                    Ok("released".to_string())
                })
            }));
        }
        wait_until(|| pool.active_jobs() == 2);
        let session = if cancel {
            "queued-cancel"
        } else {
            "queued-deadline"
        };
        let (guard, queued_control) =
            control(&registry, 400, session, if cancel { 5_000 } else { 40 });
        let invoked = Arc::new(AtomicUsize::new(0));
        let invoked_task = Arc::clone(&invoked);
        let pool_call = pool.clone();
        let handle = thread::spawn(move || {
            pool_call.execute(&queued_control, move || {
                invoked_task.fetch_add(1, Ordering::SeqCst);
                Ok("unexpected".to_string())
            })
        });
        wait_until(|| pool.queued_jobs() == 1);
        if cancel {
            registry
                .cancel_session(session, &format!("cancel-{session}"))
                .unwrap();
        }
        let result = handle.join().unwrap();
        assert!(matches!(
            result,
            Err(OcrPoolError::Cancelled {
                stage: OcrJobStage::Queued
            }) | Err(OcrPoolError::DeadlineExceeded {
                stage: OcrJobStage::Queued
            })
        ));
        assert_eq!(invoked.load(Ordering::SeqCst), 0);
        open_gate(&gate);
        for blocker in blockers {
            blocker.join().unwrap().unwrap();
        }
        wait_until(|| pool.queued_jobs() == 0);
        assert_eq!(invoked.load(Ordering::SeqCst), 0);
        drop((guard, blocker_guards));
    }

    #[test]
    fn running_cancel_discards_late_result() {
        running_control_failure_discards_late_result(true);
    }

    #[test]
    fn running_deadline_discards_late_result() {
        running_control_failure_discards_late_result(false);
    }

    #[test]
    fn timed_out_worker_slot_is_not_reused_early() {
        let pool = OcrWorkerPool::new(1, 2).unwrap();
        let registry = WindowLaneRegistry::new();
        let (_first_guard, first_control) = control(&registry, 550, "slow-timeout", 40);
        let first_gate = release_gate();
        let task_gate = Arc::clone(&first_gate);
        let first_pool = pool.clone();
        let first = thread::spawn(move || {
            first_pool.execute(&first_control, move || {
                wait_gate(&task_gate);
                Ok("late".to_string())
            })
        });
        wait_until(|| pool.active_jobs() == 1);
        assert!(matches!(
            first.join().unwrap(),
            Err(OcrPoolError::DeadlineExceeded {
                stage: OcrJobStage::Running
            })
        ));

        let (_second_guard, second_control) = control(&registry, 551, "next-job", 5_000);
        let second_invoked = Arc::new(AtomicUsize::new(0));
        let invoked = Arc::clone(&second_invoked);
        let second_pool = pool.clone();
        let second = thread::spawn(move || {
            second_pool.execute(&second_control, move || {
                invoked.fetch_add(1, Ordering::SeqCst);
                Ok("next".to_string())
            })
        });
        wait_until(|| pool.queued_jobs() == 1);
        thread::sleep(Duration::from_millis(30));
        assert_eq!(second_invoked.load(Ordering::SeqCst), 0);
        assert_eq!(pool.active_jobs(), 1);

        open_gate(&first_gate);
        assert_eq!(second.join().unwrap().unwrap(), "next");
        assert_eq!(second_invoked.load(Ordering::SeqCst), 1);
    }

    fn running_control_failure_discards_late_result(cancel: bool) {
        let pool = OcrWorkerPool::new(1, 2).unwrap();
        let registry = WindowLaneRegistry::new();
        let session = if cancel {
            "running-cancel"
        } else {
            "running-deadline"
        };
        let (guard, running_control) =
            control(&registry, 500, session, if cancel { 5_000 } else { 40 });
        let gate = release_gate();
        let task_gate = Arc::clone(&gate);
        let pool_call = pool.clone();
        let handle = thread::spawn(move || {
            pool_call.execute(&running_control, move || {
                wait_gate(&task_gate);
                Ok("late-success".to_string())
            })
        });
        wait_until(|| pool.active_jobs() == 1);
        if cancel {
            registry
                .cancel_session(session, &format!("cancel-{session}"))
                .unwrap();
        }
        let started = Instant::now();
        let result = handle.join().unwrap();
        assert!(started.elapsed() < Duration::from_millis(200));
        assert!(matches!(
            result,
            Err(OcrPoolError::Cancelled {
                stage: OcrJobStage::Running
            }) | Err(OcrPoolError::DeadlineExceeded {
                stage: OcrJobStage::Running
            })
        ));
        assert_eq!(pool.active_jobs(), 1);
        open_gate(&gate);
        wait_until(|| pool.active_jobs() == 0);
        drop(guard);
    }

    #[test]
    fn backend_panic_keeps_worker_pool_available() {
        let pool = OcrWorkerPool::new(1, 2).unwrap();
        let registry = WindowLaneRegistry::new();
        let (_guard1, first) = control(&registry, 600, "panic", 5_000);
        assert!(matches!(
            pool.execute(&first, || panic!("backend panic")),
            Err(OcrPoolError::WorkerUnavailable(_))
        ));
        let (_guard2, second) = control(&registry, 601, "after-panic", 5_000);
        assert_eq!(
            pool.execute(&second, || Ok("healthy".to_string())).unwrap(),
            "healthy"
        );
    }
}
