use serde::Deserialize;
use std::{
    collections::{HashMap, HashSet, VecDeque},
    error::Error,
    fmt,
    sync::{Arc, Condvar, Mutex, MutexGuard},
    time::{Duration, Instant},
};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
struct SessionKey {
    session_id: String,
    cancel_token_id: String,
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ExecutionContextInput {
    pub session_id: String,
    pub step_id: String,
    pub deadline_ms: u64,
    pub cancel_token_id: String,
}

#[derive(Debug, Clone)]
pub struct ExecutionContext {
    pub session_id: String,
    pub step_id: String,
    pub deadline_ms: u64,
    pub cancel_token_id: String,
    deadline_at: Instant,
}

impl ExecutionContext {
    fn new(input: ExecutionContextInput) -> Self {
        let started_at = Instant::now();
        let deadline_at = started_at
            .checked_add(Duration::from_millis(input.deadline_ms))
            .unwrap_or(started_at);
        Self {
            session_id: input.session_id,
            step_id: input.step_id,
            deadline_ms: input.deadline_ms,
            cancel_token_id: input.cancel_token_id,
            deadline_at,
        }
    }

    pub fn remaining(&self) -> Option<Duration> {
        self.deadline_at.checked_duration_since(Instant::now())
    }

    pub fn deadline_exceeded(&self) -> bool {
        Instant::now() >= self.deadline_at
    }

    fn session_key(&self) -> SessionKey {
        SessionKey {
            session_id: self.session_id.clone(),
            cancel_token_id: self.cancel_token_id.clone(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WindowLaneError {
    Cancelled {
        session_id: String,
        cancel_token_id: String,
    },
    DeadlineExceeded {
        session_id: String,
        step_id: String,
        deadline_ms: u64,
    },
    SynchronizationPoisoned,
}

impl fmt::Display for WindowLaneError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Cancelled {
                session_id,
                cancel_token_id,
            } => write!(
                f,
                "session {session_id} was cancelled by token {cancel_token_id}"
            ),
            Self::DeadlineExceeded {
                session_id,
                step_id,
                deadline_ms,
            } => write!(
                f,
                "session {session_id} step {step_id} exceeded its {deadline_ms}ms deadline"
            ),
            Self::SynchronizationPoisoned => write!(f, "window lane synchronization was poisoned"),
        }
    }
}

impl Error for WindowLaneError {}

#[derive(Debug, Default)]
struct LaneState {
    active: bool,
    queue: VecDeque<u64>,
}

#[derive(Debug, Default)]
struct RegistryState {
    lanes: HashMap<isize, LaneState>,
    active_sessions: HashMap<SessionKey, Arc<Mutex<()>>>,
    cancelled_sessions: HashSet<SessionKey>,
    next_ticket: u64,
}

#[derive(Debug, Default)]
struct RegistryInner {
    state: Mutex<RegistryState>,
    changed: Condvar,
}

#[derive(Debug, Clone, Default)]
pub struct WindowLaneRegistry {
    inner: Arc<RegistryInner>,
}

impl WindowLaneRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn acquire(
        &self,
        hwnd: isize,
        input: ExecutionContextInput,
    ) -> Result<WindowLaneGuard, WindowLaneError> {
        let context = ExecutionContext::new(input);
        let mut state = self.lock_state()?;
        let session_gate = Arc::clone(
            state
                .active_sessions
                .entry(context.session_key())
                .or_insert_with(|| Arc::new(Mutex::new(()))),
        );
        Self::check_context_locked(&state, &context)?;

        let ticket = state.next_ticket;
        state.next_ticket = state.next_ticket.wrapping_add(1);
        state.lanes.entry(hwnd).or_default().queue.push_back(ticket);

        loop {
            if let Err(error) = Self::check_context_locked(&state, &context) {
                Self::remove_waiter(&mut state, hwnd, ticket);
                self.inner.changed.notify_all();
                return Err(error);
            }

            let can_enter = state
                .lanes
                .get(&hwnd)
                .is_some_and(|lane| !lane.active && lane.queue.front() == Some(&ticket));
            if can_enter {
                let lane = state
                    .lanes
                    .get_mut(&hwnd)
                    .expect("lane exists while its ticket is queued");
                let popped = lane.queue.pop_front();
                debug_assert_eq!(popped, Some(ticket));
                lane.active = true;
                drop(state);
                return Ok(WindowLaneGuard {
                    hwnd,
                    context,
                    session_gate,
                    inner: Arc::clone(&self.inner),
                    released: false,
                });
            }

            let remaining = context.remaining().unwrap_or(Duration::ZERO);
            match self.inner.changed.wait_timeout(state, remaining) {
                Ok((next_state, _)) => state = next_state,
                Err(poisoned) => {
                    let (mut poisoned_state, _) = poisoned.into_inner();
                    Self::remove_waiter(&mut poisoned_state, hwnd, ticket);
                    self.inner.changed.notify_all();
                    return Err(WindowLaneError::SynchronizationPoisoned);
                }
            }
        }
    }

    pub fn cancel_session(
        &self,
        session_id: &str,
        cancel_token_id: &str,
    ) -> Result<bool, WindowLaneError> {
        let key = SessionKey {
            session_id: session_id.to_owned(),
            cancel_token_id: cancel_token_id.to_owned(),
        };
        let session_gate = {
            let state = self.lock_state()?;
            state.active_sessions.get(&key).cloned()
        };
        let Some(session_gate) = session_gate else {
            return Ok(false);
        };
        let _commit_guard = session_gate
            .lock()
            .map_err(|_| WindowLaneError::SynchronizationPoisoned)?;
        let mut state = self.lock_state()?;
        let still_active = state
            .active_sessions
            .get(&key)
            .is_some_and(|active| Arc::ptr_eq(active, &session_gate));
        let newly_cancelled = still_active && state.cancelled_sessions.insert(key);
        drop(state);
        self.inner.changed.notify_all();
        Ok(newly_cancelled)
    }

    pub fn complete_session(
        &self,
        session_id: &str,
        cancel_token_id: &str,
    ) -> Result<bool, WindowLaneError> {
        let key = SessionKey {
            session_id: session_id.to_owned(),
            cancel_token_id: cancel_token_id.to_owned(),
        };
        let session_gate = {
            let state = self.lock_state()?;
            state.active_sessions.get(&key).cloned()
        };
        let Some(session_gate) = session_gate else {
            return Ok(false);
        };
        let _commit_guard = session_gate
            .lock()
            .map_err(|_| WindowLaneError::SynchronizationPoisoned)?;
        let mut state = self.lock_state()?;
        let was_active = state
            .active_sessions
            .get(&key)
            .is_some_and(|active| Arc::ptr_eq(active, &session_gate));
        if was_active {
            state.active_sessions.remove(&key);
        }
        state.cancelled_sessions.remove(&key);
        drop(state);
        self.inner.changed.notify_all();
        Ok(was_active)
    }

    #[cfg(test)]
    pub fn check_context(&self, context: &ExecutionContext) -> Result<(), WindowLaneError> {
        let state = self.lock_state()?;
        Self::check_context_locked(&state, context)
    }

    fn lock_state(&self) -> Result<MutexGuard<'_, RegistryState>, WindowLaneError> {
        self.inner
            .state
            .lock()
            .map_err(|_| WindowLaneError::SynchronizationPoisoned)
    }

    fn check_context_locked(
        state: &RegistryState,
        context: &ExecutionContext,
    ) -> Result<(), WindowLaneError> {
        if state.cancelled_sessions.contains(&context.session_key()) {
            return Err(WindowLaneError::Cancelled {
                session_id: context.session_id.clone(),
                cancel_token_id: context.cancel_token_id.clone(),
            });
        }
        if context.deadline_exceeded() {
            return Err(WindowLaneError::DeadlineExceeded {
                session_id: context.session_id.clone(),
                step_id: context.step_id.clone(),
                deadline_ms: context.deadline_ms,
            });
        }
        Ok(())
    }

    fn remove_waiter(state: &mut RegistryState, hwnd: isize, ticket: u64) {
        let remove_lane = if let Some(lane) = state.lanes.get_mut(&hwnd) {
            if let Some(index) = lane.queue.iter().position(|queued| *queued == ticket) {
                lane.queue.remove(index);
            }
            !lane.active && lane.queue.is_empty()
        } else {
            false
        };
        if remove_lane {
            state.lanes.remove(&hwnd);
        }
    }
}

#[derive(Debug)]
pub struct WindowLaneGuard {
    hwnd: isize,
    context: ExecutionContext,
    session_gate: Arc<Mutex<()>>,
    inner: Arc<RegistryInner>,
    released: bool,
}

impl WindowLaneGuard {
    #[cfg(test)]
    pub fn context(&self) -> &ExecutionContext {
        &self.context
    }

    pub fn control(&self) -> ExecutionControl {
        ExecutionControl {
            context: self.context.clone(),
            session_gate: Arc::clone(&self.session_gate),
            inner: Arc::clone(&self.inner),
        }
    }

    fn release_inner(&mut self) {
        if self.released {
            return;
        }
        self.released = true;

        let Ok(mut state) = self.inner.state.lock() else {
            self.inner.changed.notify_all();
            return;
        };
        let remove_lane = if let Some(lane) = state.lanes.get_mut(&self.hwnd) {
            lane.active = false;
            lane.queue.is_empty()
        } else {
            false
        };
        if remove_lane {
            state.lanes.remove(&self.hwnd);
        }
        drop(state);
        self.inner.changed.notify_all();
    }
}

impl Drop for WindowLaneGuard {
    fn drop(&mut self) {
        self.release_inner();
    }
}

#[derive(Debug, Clone)]
pub struct ExecutionControl {
    context: ExecutionContext,
    session_gate: Arc<Mutex<()>>,
    inner: Arc<RegistryInner>,
}

impl ExecutionControl {
    pub fn check_typed(&self) -> Result<(), WindowLaneError> {
        let state = self
            .inner
            .state
            .lock()
            .map_err(|_| WindowLaneError::SynchronizationPoisoned)?;
        WindowLaneRegistry::check_context_locked(&state, &self.context)
    }

    pub fn remaining(&self) -> Option<Duration> {
        self.context.remaining()
    }

    pub fn checkpoint(&self) -> Result<(), String> {
        self.check_typed().map_err(|error| error.to_string())
    }

    pub fn commit_input<T>(&self, action: impl FnOnce() -> Result<T, String>) -> Result<T, String> {
        let _commit_guard = self
            .session_gate
            .lock()
            .map_err(|_| WindowLaneError::SynchronizationPoisoned.to_string())?;
        let state = self
            .inner
            .state
            .lock()
            .map_err(|_| WindowLaneError::SynchronizationPoisoned.to_string())?;
        WindowLaneRegistry::check_context_locked(&state, &self.context)
            .map_err(|error| error.to_string())?;
        drop(state);
        action()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        sync::{
            atomic::{AtomicUsize, Ordering},
            mpsc, Arc, Mutex,
        },
        thread,
    };

    fn input(session: &str, step: &str, deadline_ms: u64) -> ExecutionContextInput {
        ExecutionContextInput {
            session_id: session.to_owned(),
            step_id: step.to_owned(),
            deadline_ms,
            cancel_token_id: format!("cancel-{session}"),
        }
    }

    fn wait_for_queue_len(registry: &WindowLaneRegistry, hwnd: isize, expected: usize) {
        let timeout = Instant::now() + Duration::from_secs(2);
        loop {
            let queued = registry
                .inner
                .state
                .lock()
                .unwrap()
                .lanes
                .get(&hwnd)
                .map_or(0, |lane| lane.queue.len());
            if queued == expected {
                return;
            }
            assert!(
                Instant::now() < timeout,
                "queue length did not reach {expected}"
            );
            thread::yield_now();
        }
    }

    fn update_max(maximum: &AtomicUsize, value: usize) {
        let mut observed = maximum.load(Ordering::SeqCst);
        while value > observed {
            match maximum.compare_exchange(observed, value, Ordering::SeqCst, Ordering::SeqCst) {
                Ok(_) => return,
                Err(actual) => observed = actual,
            }
        }
    }

    #[test]
    fn same_hwnd_is_fifo_and_never_executes_more_than_one_request() {
        let registry = WindowLaneRegistry::new();
        let initial = registry.acquire(100, input("holder", "0", 2_000)).unwrap();
        let active = Arc::new(AtomicUsize::new(0));
        let maximum = Arc::new(AtomicUsize::new(0));
        let order = Arc::new(Mutex::new(Vec::new()));
        let mut threads = Vec::new();

        for index in 1..=3 {
            let waiter_registry = registry.clone();
            let active = Arc::clone(&active);
            let maximum = Arc::clone(&maximum);
            let order = Arc::clone(&order);
            threads.push(thread::spawn(move || {
                let _guard = waiter_registry
                    .acquire(
                        100,
                        input(&format!("session-{index}"), &index.to_string(), 2_000),
                    )
                    .unwrap();
                let now_active = active.fetch_add(1, Ordering::SeqCst) + 1;
                update_max(&maximum, now_active);
                order.lock().unwrap().push(index);
                thread::sleep(Duration::from_millis(15));
                active.fetch_sub(1, Ordering::SeqCst);
            }));
            wait_for_queue_len(&registry, 100, index);
        }

        drop(initial);
        for thread in threads {
            thread.join().unwrap();
        }

        assert_eq!(maximum.load(Ordering::SeqCst), 1);
        assert_eq!(*order.lock().unwrap(), vec![1, 2, 3]);
    }

    #[test]
    fn different_hwnds_can_overlap() {
        let registry = WindowLaneRegistry::new();
        let (entered_tx, entered_rx) = mpsc::channel();
        let (release_tx, release_rx) = mpsc::channel();
        let release_rx = Arc::new(Mutex::new(release_rx));
        let mut threads = Vec::new();

        for hwnd in [101, 202] {
            let registry = registry.clone();
            let entered_tx = entered_tx.clone();
            let release_rx = Arc::clone(&release_rx);
            threads.push(thread::spawn(move || {
                let _guard = registry
                    .acquire(hwnd, input(&format!("session-{hwnd}"), "step", 2_000))
                    .unwrap();
                entered_tx.send(hwnd).unwrap();
                release_rx.lock().unwrap().recv().unwrap();
            }));
        }

        let first = entered_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        let second = entered_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        assert_ne!(first, second);
        release_tx.send(()).unwrap();
        release_tx.send(()).unwrap();
        for thread in threads {
            thread.join().unwrap();
        }
    }

    #[test]
    fn cancelling_a_session_wakes_and_rejects_its_waiter() {
        let registry = WindowLaneRegistry::new();
        let holder = registry.acquire(303, input("holder", "0", 2_000)).unwrap();
        let waiter_registry = registry.clone();
        let (result_tx, result_rx) = mpsc::channel();
        let waiter = thread::spawn(move || {
            result_tx
                .send(waiter_registry.acquire(303, input("cancelled", "1", 2_000)))
                .unwrap();
        });
        wait_for_queue_len(&registry, 303, 1);

        registry
            .cancel_session("cancelled", "cancel-cancelled")
            .unwrap();
        let error = result_rx
            .recv_timeout(Duration::from_secs(1))
            .unwrap()
            .unwrap_err();
        assert_eq!(
            error,
            WindowLaneError::Cancelled {
                session_id: "cancelled".to_owned(),
                cancel_token_id: "cancel-cancelled".to_owned(),
            }
        );
        waiter.join().unwrap();
        drop(holder);
    }

    #[test]
    fn completed_session_releases_cancellation_state_and_rejects_late_cancel() {
        let registry = WindowLaneRegistry::new();
        let guard = registry
            .acquire(505, input("completed", "1", 2_000))
            .unwrap();
        registry
            .cancel_session("completed", "cancel-completed")
            .unwrap();
        drop(guard);

        assert!(registry
            .complete_session("completed", "cancel-completed")
            .unwrap());
        assert!(!registry
            .cancel_session("completed", "cancel-completed")
            .unwrap());

        let next = registry
            .acquire(505, input("completed", "2", 2_000))
            .unwrap();
        drop(next);
    }

    #[test]
    fn cancellation_requires_the_matching_token() {
        let registry = WindowLaneRegistry::new();
        let guard = registry.acquire(606, input("tokened", "1", 2_000)).unwrap();

        assert!(!registry.cancel_session("tokened", "wrong-token").unwrap());
        registry.check_context(guard.context()).unwrap();
        assert!(registry
            .cancel_session("tokened", "cancel-tokened")
            .unwrap());
        assert!(matches!(
            registry.check_context(guard.context()),
            Err(WindowLaneError::Cancelled { .. })
        ));
    }

    #[test]
    fn cancelled_before_input_commit_never_calls_the_action() {
        let registry = WindowLaneRegistry::new();
        let guard = registry
            .acquire(707, input("cancel-before-input", "1", 2_000))
            .unwrap();
        let control = guard.control();
        let calls = AtomicUsize::new(0);

        registry
            .cancel_session("cancel-before-input", "cancel-cancel-before-input")
            .unwrap();
        let error = control
            .commit_input(|| {
                calls.fetch_add(1, Ordering::SeqCst);
                Ok(())
            })
            .unwrap_err();

        assert!(error.contains("was cancelled"));
        assert_eq!(calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn deadline_before_input_commit_never_calls_the_action() {
        let registry = WindowLaneRegistry::new();
        let guard = registry
            .acquire(808, input("deadline-before-input", "1", 20))
            .unwrap();
        let control = guard.control();
        let calls = AtomicUsize::new(0);
        thread::sleep(Duration::from_millis(30));

        let error = control
            .commit_input(|| {
                calls.fetch_add(1, Ordering::SeqCst);
                Ok(())
            })
            .unwrap_err();

        assert!(error.contains("exceeded its 20ms deadline"));
        assert_eq!(calls.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn input_commit_and_cancel_are_linearized_per_session() {
        let registry = WindowLaneRegistry::new();
        let guard = registry
            .acquire(909, input("linearized", "1", 2_000))
            .unwrap();
        let control = guard.control();
        let (entered_tx, entered_rx) = mpsc::channel();
        let (release_tx, release_rx) = mpsc::channel();
        let input_thread = thread::spawn(move || {
            control
                .commit_input(|| {
                    entered_tx.send(()).unwrap();
                    release_rx.recv().unwrap();
                    Ok(())
                })
                .unwrap();
        });
        entered_rx.recv_timeout(Duration::from_secs(1)).unwrap();

        let cancel_registry = registry.clone();
        let (cancel_tx, cancel_rx) = mpsc::channel();
        let cancel_thread = thread::spawn(move || {
            cancel_tx
                .send(
                    cancel_registry
                        .cancel_session("linearized", "cancel-linearized")
                        .unwrap(),
                )
                .unwrap();
        });
        assert!(cancel_rx.recv_timeout(Duration::from_millis(40)).is_err());

        release_tx.send(()).unwrap();
        input_thread.join().unwrap();
        assert!(cancel_rx.recv_timeout(Duration::from_secs(1)).unwrap());
        cancel_thread.join().unwrap();
    }

    #[test]
    fn different_sessions_can_commit_input_concurrently() {
        let registry = WindowLaneRegistry::new();
        let first = registry
            .acquire(1001, input("commit-a", "1", 2_000))
            .unwrap()
            .control();
        let second = registry
            .acquire(1002, input("commit-b", "1", 2_000))
            .unwrap()
            .control();
        let (entered_tx, entered_rx) = mpsc::channel();
        let (release_tx, release_rx) = mpsc::channel();
        let release_rx = Arc::new(Mutex::new(release_rx));
        let mut threads = Vec::new();

        for control in [first, second] {
            let entered_tx = entered_tx.clone();
            let release_rx = Arc::clone(&release_rx);
            threads.push(thread::spawn(move || {
                control
                    .commit_input(|| {
                        entered_tx.send(()).unwrap();
                        release_rx.lock().unwrap().recv().unwrap();
                        Ok(())
                    })
                    .unwrap();
            }));
        }

        entered_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        entered_rx.recv_timeout(Duration::from_secs(1)).unwrap();
        release_tx.send(()).unwrap();
        release_tx.send(()).unwrap();
        for thread in threads {
            thread.join().unwrap();
        }
    }

    #[test]
    fn waiting_request_fails_closed_when_its_deadline_expires() {
        let registry = WindowLaneRegistry::new();
        let holder = registry.acquire(404, input("holder", "0", 2_000)).unwrap();
        let waiter_registry = registry.clone();
        let (result_tx, result_rx) = mpsc::channel();
        let waiter = thread::spawn(move || {
            result_tx
                .send(waiter_registry.acquire(404, input("deadline", "1", 40)))
                .unwrap();
        });
        wait_for_queue_len(&registry, 404, 1);

        let error = result_rx
            .recv_timeout(Duration::from_secs(1))
            .unwrap()
            .unwrap_err();
        assert_eq!(
            error,
            WindowLaneError::DeadlineExceeded {
                session_id: "deadline".to_owned(),
                step_id: "1".to_owned(),
                deadline_ms: 40,
            }
        );
        waiter.join().unwrap();
        drop(holder);
    }
}
