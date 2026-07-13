pub mod capture_health;
pub mod ocr_pool;
pub mod vision_match;
pub mod window_lane;

#[allow(unused_imports)]
pub use capture_health::{
    apply_health_to_captured_frame, analyze_rgb_frame, classify_control_frame, sample_from_captured,
    CaptureHealthIssue, CaptureHealthReport, FrameHealthSample,
};
pub use ocr_pool::{OcrJobStage, OcrPoolError, OcrWorkerPool};
pub use vision_match::{
    enforce_search_budget, estimate_search_budget, match_only_without_template_status,
    match_template_budgeted, SearchBudgetReport, SearchRoi, TemplateMatch as VisionTemplateMatch,
    MAX_TEMPLATE_COMPARE_PIXELS, MAX_TEMPLATE_SEARCH_POSITIONS,
};
pub use window_lane::{ExecutionContextInput, ExecutionControl, WindowLaneRegistry};
