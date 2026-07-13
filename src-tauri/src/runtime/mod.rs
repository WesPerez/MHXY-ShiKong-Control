pub mod capture_health;
pub mod ocr_pool;
pub mod vision_match;
pub mod window_lane;

#[allow(unused_imports)]
pub use capture_health::{
    analyze_rgb_frame, apply_health_to_captured_frame, classify_control_frame,
    sample_from_captured, CaptureHealthIssue, CaptureHealthReport, FrameHealthSample,
};
pub use ocr_pool::{OcrJobStage, OcrPoolError, OcrWorkerPool};
pub use vision_match::{match_only_without_template_status, match_template_budgeted, SearchRoi};
pub use window_lane::{ExecutionContextInput, ExecutionControl, WindowLaneRegistry};
