//! Read-only strict HWND capture and match-only preflight probe.
//!
//! This binary calls only capture and template-matching code. It does not
//! initialize Tauri, dispatch workflow steps, or call any input API. Its
//! integration test also rejects final PE imports for all input APIs.

#[path = "../runtime/capture_health.rs"]
mod capture_health;
#[allow(dead_code)]
#[path = "../platform.rs"]
mod platform;
#[allow(dead_code)]
#[path = "../runtime/vision_match.rs"]
mod vision_match;

use capture_health::apply_health_to_captured_frame;
use image::ImageReader;
use platform::{capture_client_rgb_strict, window_for_hwnd, AppWindow, RgbFrame};
use serde::Serialize;
use std::{env, path::PathBuf, process, thread, time::Duration};
use vision_match::{match_template_budgeted, SearchRoi, TemplateMatch};

const OUTPUT_MARKER: &str = "STRICT_CAPTURE_PROBE_JSON=";

#[derive(Debug, Clone)]
struct ProbeArgs {
    hwnd: isize,
    template: PathBuf,
    roi: SearchRoi,
    threshold: f32,
    samples: u32,
    interval_ms: u64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct TargetWindow {
    hwnd: isize,
    pid: u32,
    title: String,
    process_name: String,
    client_width: u32,
    client_height: u32,
}

impl From<&AppWindow> for TargetWindow {
    fn from(window: &AppWindow) -> Self {
        Self {
            hwnd: window.hwnd,
            pid: window.process_id,
            title: window.title.clone(),
            process_name: window.process_name.clone(),
            client_width: window.client_width,
            client_height: window.client_height,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct MatchBox {
    x: u32,
    y: u32,
    width: u32,
    height: u32,
    score: f32,
}

impl From<TemplateMatch> for MatchBox {
    fn from(matched: TemplateMatch) -> Self {
        Self {
            x: matched.x,
            y: matched.y,
            width: matched.width,
            height: matched.height,
            score: matched.score,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct SampleObservation {
    index: u32,
    frame_hash: String,
    frame_hash_repeated_from_previous: bool,
    captured_at_ms: u64,
    capture_provider: platform::CaptureProvider,
    capture_reliability: platform::CaptureReliability,
    fallback_used: bool,
    strict_target_source: bool,
    control_eligible: bool,
    matched: bool,
    match_box: MatchBox,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct WaitImageSummary {
    action: &'static str,
    matched: bool,
    threshold: f32,
    sample_count: u32,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct ProbeReport {
    kind: &'static str,
    version: u32,
    input_sent: bool,
    target: TargetWindow,
    template_path: String,
    roi: SearchRoiRecord,
    samples: Vec<SampleObservation>,
    wait_image: WaitImageSummary,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct SearchRoiRecord {
    x: u32,
    y: u32,
    width: u32,
    height: u32,
}

impl From<SearchRoi> for SearchRoiRecord {
    fn from(roi: SearchRoi) -> Self {
        Self {
            x: roi.x,
            y: roi.y,
            width: roi.w,
            height: roi.h,
        }
    }
}

fn usage() -> &'static str {
    "Usage: strict_capture_probe --hwnd <HWND> --template <IMAGE> --roi <x,y,width,height> --threshold <0..1> [--samples <2..8>] [--interval-ms <50..5000>]"
}

fn option_value(arguments: &[String], index: &mut usize, name: &str) -> Result<String, String> {
    *index += 1;
    arguments
        .get(*index)
        .cloned()
        .ok_or_else(|| format!("{name} requires a value"))
}

fn parse_u32(value: &str, name: &str) -> Result<u32, String> {
    value
        .parse::<u32>()
        .map_err(|_| format!("{name} must be an unsigned integer"))
}

fn parse_roi(value: &str) -> Result<SearchRoi, String> {
    let parts: Vec<&str> = value.split(',').collect();
    if parts.len() != 4 {
        return Err("--roi must use x,y,width,height".to_string());
    }
    let x = parse_u32(parts[0].trim(), "roi x")?;
    let y = parse_u32(parts[1].trim(), "roi y")?;
    let w = parse_u32(parts[2].trim(), "roi width")?;
    let h = parse_u32(parts[3].trim(), "roi height")?;
    if w == 0 || h == 0 {
        return Err("--roi width and height must be positive".to_string());
    }
    Ok(SearchRoi { x, y, w, h })
}

fn parse_args() -> Result<ProbeArgs, String> {
    let arguments: Vec<String> = env::args().skip(1).collect();
    if arguments
        .iter()
        .any(|argument| argument == "--help" || argument == "-h")
    {
        println!("{}", usage());
        process::exit(0);
    }

    let mut hwnd = None;
    let mut template = None;
    let mut roi = None;
    let mut threshold = None;
    let mut samples = 2u32;
    let mut interval_ms = 250u64;
    let mut index = 0usize;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--hwnd" => {
                let value = option_value(&arguments, &mut index, "--hwnd")?;
                let parsed = value
                    .parse::<i64>()
                    .map_err(|_| "--hwnd must be an integer".to_string())?;
                if parsed <= 0 {
                    return Err("--hwnd must be positive".to_string());
                }
                hwnd = Some(parsed as isize);
            }
            "--template" => {
                template = Some(PathBuf::from(option_value(
                    &arguments,
                    &mut index,
                    "--template",
                )?));
            }
            "--roi" => {
                roi = Some(parse_roi(&option_value(&arguments, &mut index, "--roi")?)?);
            }
            "--threshold" => {
                let value = option_value(&arguments, &mut index, "--threshold")?;
                let parsed = value
                    .parse::<f32>()
                    .map_err(|_| "--threshold must be a number".to_string())?;
                if !parsed.is_finite() || !(0.0..=1.0).contains(&parsed) {
                    return Err("--threshold must be within 0..1".to_string());
                }
                threshold = Some(parsed);
            }
            "--samples" => {
                let value = option_value(&arguments, &mut index, "--samples")?;
                samples = parse_u32(&value, "--samples")?;
            }
            "--interval-ms" => {
                let value = option_value(&arguments, &mut index, "--interval-ms")?;
                interval_ms = value
                    .parse::<u64>()
                    .map_err(|_| "--interval-ms must be an unsigned integer".to_string())?;
            }
            unknown => return Err(format!("unknown argument {unknown}; {}", usage())),
        }
        index += 1;
    }

    if !(2..=8).contains(&samples) {
        return Err("--samples must be within 2..8".to_string());
    }
    if !(50..=5_000).contains(&interval_ms) {
        return Err("--interval-ms must be within 50..5000".to_string());
    }
    let template = template.ok_or_else(|| "--template is required".to_string())?;
    if !template.is_file() {
        return Err(format!("template image is missing: {}", template.display()));
    }
    Ok(ProbeArgs {
        hwnd: hwnd.ok_or_else(|| "--hwnd is required".to_string())?,
        template,
        roi: roi.ok_or_else(|| "--roi is required for bounded match-only search".to_string())?,
        threshold: threshold.ok_or_else(|| "--threshold is required".to_string())?,
        samples,
        interval_ms,
    })
}

fn load_image_rgb(path: &PathBuf) -> Result<RgbFrame, String> {
    let image = ImageReader::open(path)
        .map_err(|error| format!("{}: {error}", path.display()))?
        .decode()
        .map_err(|error| format!("{}: {error}", path.display()))?
        .to_rgb8();
    Ok(RgbFrame {
        width: image.width(),
        height: image.height(),
        pixels: image.into_raw(),
    })
}

fn verify_same_target(expected: &TargetWindow, actual: &TargetWindow) -> Result<(), String> {
    if expected.hwnd != actual.hwnd
        || expected.pid != actual.pid
        || expected.process_name != actual.process_name
        || expected.title != actual.title
        || expected.client_width != actual.client_width
        || expected.client_height != actual.client_height
    {
        return Err("target window identity changed during strict capture observation".to_string());
    }
    Ok(())
}

fn repeated_hash(previous: Option<&str>, current: &str) -> bool {
    previous.is_some_and(|value| value == current)
}

fn capture_with_verified_target<T, W, C>(
    expected: &TargetWindow,
    mut read_window: W,
    mut capture: C,
) -> Result<T, String>
where
    W: FnMut() -> Result<TargetWindow, String>,
    C: FnMut() -> Result<T, String>,
{
    verify_same_target(expected, &read_window()?)?;
    let captured = capture()?;
    verify_same_target(expected, &read_window()?)?;
    Ok(captured)
}

fn run_probe(args: ProbeArgs) -> Result<ProbeReport, String> {
    let target_window = window_for_hwnd(args.hwnd)?;
    if target_window.client_width == 0 || target_window.client_height == 0 {
        return Err("target window has an empty client area".to_string());
    }
    let target = TargetWindow::from(&target_window);
    let template = load_image_rgb(&args.template)?;
    let mut observations = Vec::with_capacity(args.samples as usize);
    let mut previous_hash = None::<String>;
    let mut any_match = false;

    for index in 0..args.samples {
        let captured = capture_with_verified_target(
            &target,
            || Ok(TargetWindow::from(&window_for_hwnd(args.hwnd)?)),
            || capture_client_rgb_strict(args.hwnd),
        )?;
        // A still game page can legitimately produce the same hash. Staleness is
        // only meaningful when a caller explicitly expects visual change, so this
        // read-only wait-image probe intentionally provides no prior sample.
        let captured = apply_health_to_captured_frame(
            captured,
            Some(target.client_width),
            Some(target.client_height),
            None,
        );
        let metadata = captured.metadata.clone();
        if !metadata.permits_control_decision() {
            return Err(format!(
                "strict capture is not health-verified: {:?}/{:?}",
                metadata.provider, metadata.reliability
            ));
        }

        let matched =
            match_template_budgeted(&captured.rgb, &template, Some(args.roi), true, || Ok(()))?;
        let match_box = MatchBox::from(matched);
        let is_match = match_box.score >= args.threshold;
        any_match = any_match || is_match;
        let repeated = repeated_hash(previous_hash.as_deref(), &metadata.frame_hash);
        previous_hash = Some(metadata.frame_hash.clone());
        let strict_target_source = metadata.is_strict_target_source();
        let control_eligible = metadata.permits_control_decision();
        observations.push(SampleObservation {
            index: index + 1,
            frame_hash: metadata.frame_hash,
            frame_hash_repeated_from_previous: repeated,
            captured_at_ms: metadata.captured_at_ms,
            capture_provider: metadata.provider,
            capture_reliability: metadata.reliability,
            fallback_used: metadata.fallback_used,
            strict_target_source,
            control_eligible,
            matched: is_match,
            match_box,
        });
        if index + 1 < args.samples {
            thread::sleep(Duration::from_millis(args.interval_ms));
        }
    }
    verify_same_target(&target, &TargetWindow::from(&window_for_hwnd(args.hwnd)?))?;

    Ok(ProbeReport {
        kind: "mhxy-shikong.strict-capture-preflight",
        version: 1,
        input_sent: false,
        target,
        template_path: args.template.to_string_lossy().to_string(),
        roi: SearchRoiRecord::from(args.roi),
        samples: observations,
        wait_image: WaitImageSummary {
            action: "match_only",
            matched: any_match,
            threshold: args.threshold,
            sample_count: args.samples,
        },
    })
}

fn main() {
    match parse_args().and_then(run_probe) {
        Ok(report) => match serde_json::to_string(&report) {
            Ok(json) => println!("{OUTPUT_MARKER}{json}"),
            Err(error) => {
                eprintln!("strict capture probe could not serialize its report: {error}");
                process::exit(2);
            }
        },
        Err(error) => {
            eprintln!("strict capture probe failed: {error}");
            process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn target(hwnd: isize, title: &str) -> TargetWindow {
        TargetWindow {
            hwnd,
            pid: 42,
            title: title.to_string(),
            process_name: "MyGame_x64r.exe".to_string(),
            client_width: 1280,
            client_height: 720,
        }
    }

    #[test]
    fn parse_roi_requires_positive_dimensions() {
        let roi = parse_roi("10,20,30,40").expect("valid roi");
        assert_eq!((roi.x, roi.y, roi.w, roi.h), (10, 20, 30, 40));
        assert!(parse_roi("10,20,0,40").is_err());
    }

    #[test]
    fn repeated_hash_is_observation_not_capture_failure() {
        assert!(repeated_hash(Some("same"), "same"));
        assert!(!repeated_hash(Some("before"), "after"));
        assert!(!repeated_hash(None, "first"));
    }

    #[test]
    fn target_identity_change_is_rejected() {
        assert!(verify_same_target(&target(88, "Dream"), &target(88, "Dream")).is_ok());
        assert!(verify_same_target(&target(88, "Dream"), &target(89, "Dream")).is_err());
        assert!(verify_same_target(&target(88, "Dream"), &target(88, "Other")).is_err());
    }

    #[test]
    fn capture_rejects_identity_change_after_capture() {
        let expected = target(88, "Dream");
        let mut observed = vec![expected.clone(), target(89, "Dream")].into_iter();
        let result = capture_with_verified_target(
            &expected,
            || Ok(observed.next().expect("one observation per target check")),
            || Ok(()),
        );
        assert!(result.is_err());
    }
}
