//! Budgeted template matching helpers for fail-closed vision steps.

use crate::platform::RgbFrame;

/// Maximum candidate positions allowed for a single template search.
pub const MAX_TEMPLATE_SEARCH_POSITIONS: u64 = 180_000;
/// Soft pixel-compare budget: positions * template_pixels.
pub const MAX_TEMPLATE_COMPARE_PIXELS: u64 = 40_000_000;
pub const CHECKPOINT_PIXEL_BUDGET: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SearchRoi {
    pub x: u32,
    pub y: u32,
    pub w: u32,
    pub h: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TemplateMatch {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
    pub score: f32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SearchBudgetReport {
    pub positions: u64,
    pub template_pixels: u64,
    pub compare_pixels: u64,
    pub max_positions: u64,
    pub max_compare_pixels: u64,
}

impl SearchBudgetReport {
    pub fn within_budget(&self) -> bool {
        self.positions <= self.max_positions && self.compare_pixels <= self.max_compare_pixels
    }

    pub fn detail(&self) -> String {
        format!(
            "positions={} (max {}), compare_pixels={} (max {})",
            self.positions, self.max_positions, self.compare_pixels, self.max_compare_pixels
        )
    }
}

pub fn clip_search_roi(
    roi: Option<SearchRoi>,
    frame_width: u32,
    frame_height: u32,
) -> Option<SearchRoi> {
    let roi = roi.unwrap_or(SearchRoi {
        x: 0,
        y: 0,
        w: frame_width,
        h: frame_height,
    });
    if roi.w == 0 || roi.h == 0 || frame_width == 0 || frame_height == 0 {
        return None;
    }
    let x = roi.x.min(frame_width);
    let y = roi.y.min(frame_height);
    let w = roi.w.min(frame_width.saturating_sub(x));
    let h = roi.h.min(frame_height.saturating_sub(y));
    (w > 0 && h > 0).then_some(SearchRoi { x, y, w, h })
}

pub fn estimate_search_budget(
    frame_width: u32,
    frame_height: u32,
    template_width: u32,
    template_height: u32,
    search_roi: Option<SearchRoi>,
) -> Result<SearchBudgetReport, String> {
    if template_width == 0 || template_height == 0 {
        return Err("template image is empty".to_string());
    }
    if template_width > frame_width || template_height > frame_height {
        return Err(format!(
            "template {}x{} is larger than frame {}x{}",
            template_width, template_height, frame_width, frame_height
        ));
    }
    let roi = clip_search_roi(search_roi, frame_width, frame_height)
        .ok_or_else(|| "search ROI is empty after clipping".to_string())?;
    let search_right = roi.x.saturating_add(roi.w).min(frame_width);
    let search_bottom = roi.y.saturating_add(roi.h).min(frame_height);
    if search_right < roi.x.saturating_add(template_width)
        || search_bottom < roi.y.saturating_add(template_height)
    {
        return Err("search ROI is smaller than template".to_string());
    }
    let max_x = search_right - template_width;
    let max_y = search_bottom - template_height;
    let positions_x = u64::from(max_x.saturating_sub(roi.x).saturating_add(1));
    let positions_y = u64::from(max_y.saturating_sub(roi.y).saturating_add(1));
    let positions = positions_x.saturating_mul(positions_y);
    let template_pixels = u64::from(template_width).saturating_mul(u64::from(template_height));
    let compare_pixels = positions.saturating_mul(template_pixels);
    Ok(SearchBudgetReport {
        positions,
        template_pixels,
        compare_pixels,
        max_positions: MAX_TEMPLATE_SEARCH_POSITIONS,
        max_compare_pixels: MAX_TEMPLATE_COMPARE_PIXELS,
    })
}

pub fn enforce_search_budget(
    report: &SearchBudgetReport,
    has_explicit_roi: bool,
) -> Result<(), String> {
    if report.within_budget() {
        return Ok(());
    }
    if !has_explicit_roi {
        return Err(format!(
            "search_budget_exceeded: full-frame search requires a tighter ROI ({})",
            report.detail()
        ));
    }
    Err(format!(
        "search_budget_exceeded: ROI search still exceeds budget ({})",
        report.detail()
    ))
}

pub fn match_template_budgeted(
    frame: &RgbFrame,
    template: &RgbFrame,
    search_roi: Option<SearchRoi>,
    has_explicit_roi: bool,
    mut checkpoint: impl FnMut() -> Result<(), String>,
) -> Result<TemplateMatch, String> {
    checkpoint()?;
    let report = estimate_search_budget(
        frame.width,
        frame.height,
        template.width,
        template.height,
        search_roi,
    )?;
    enforce_search_budget(&report, has_explicit_roi)?;

    let roi = clip_search_roi(search_roi, frame.width, frame.height)
        .ok_or_else(|| "search ROI is empty after clipping".to_string())?;
    let search_right = roi.x.saturating_add(roi.w).min(frame.width);
    let search_bottom = roi.y.saturating_add(roi.h).min(frame.height);
    let max_x = search_right - template.width;
    let max_y = search_bottom - template.height;

    let mut best = TemplateMatch {
        x: roi.x,
        y: roi.y,
        width: template.width,
        height: template.height,
        score: f32::MIN,
    };
    let mut pixels_since_checkpoint = 0usize;
    for y in roi.y..=max_y {
        for x in roi.x..=max_x {
            let score = template_score(
                frame,
                template,
                x,
                y,
                &mut pixels_since_checkpoint,
                CHECKPOINT_PIXEL_BUDGET,
                &mut checkpoint,
            )?;
            if score > best.score {
                best.x = x;
                best.y = y;
                best.score = score;
            }
        }
    }
    checkpoint()?;
    Ok(best)
}

fn template_score(
    frame: &RgbFrame,
    template: &RgbFrame,
    left: u32,
    top: u32,
    pixels_since_checkpoint: &mut usize,
    checkpoint_pixel_budget: usize,
    checkpoint: &mut dyn FnMut() -> Result<(), String>,
) -> Result<f32, String> {
    let mut diff: u64 = 0;
    for y in 0..template.height {
        let frame_row = ((top + y) * frame.width + left) as usize * 3;
        let template_row = (y * template.width) as usize * 3;
        for x in 0..template.width as usize {
            *pixels_since_checkpoint += 1;
            if *pixels_since_checkpoint >= checkpoint_pixel_budget {
                checkpoint()?;
                *pixels_since_checkpoint = 0;
            }
            let frame_index = frame_row + x * 3;
            let template_index = template_row + x * 3;
            diff += (i16::from(frame.pixels[frame_index])
                - i16::from(template.pixels[template_index]))
            .unsigned_abs() as u64;
            diff += (i16::from(frame.pixels[frame_index + 1])
                - i16::from(template.pixels[template_index + 1]))
            .unsigned_abs() as u64;
            diff += (i16::from(frame.pixels[frame_index + 2])
                - i16::from(template.pixels[template_index + 2]))
            .unsigned_abs() as u64;
        }
    }
    let max_diff = template.width as f32 * template.height as f32 * 3.0 * 255.0;
    Ok(1.0 - (diff as f32 / max_diff))
}

/// Match-only image steps require a real template; ROI/point alone must not count as matched.
pub fn match_only_without_template_status() -> (&'static str, &'static str, bool) {
    (
        "missing_template",
        "wait/detect image step requires a bound template image; ROI/point alone cannot match",
        false,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn solid_frame(width: u32, height: u32, value: u8) -> RgbFrame {
        RgbFrame {
            width,
            height,
            pixels: vec![value; (width * height * 3) as usize],
        }
    }

    fn insert_template(frame: &mut RgbFrame, template: &RgbFrame, left: u32, top: u32) {
        for y in 0..template.height {
            for x in 0..template.width {
                let fi = (((top + y) * frame.width + left + x) * 3) as usize;
                let ti = ((y * template.width + x) * 3) as usize;
                frame.pixels[fi..fi + 3].copy_from_slice(&template.pixels[ti..ti + 3]);
            }
        }
    }

    #[test]
    fn full_frame_large_search_requires_roi() {
        let report = estimate_search_budget(1280, 720, 64, 64, None).unwrap();
        assert!(!report.within_budget());
        let err = enforce_search_budget(&report, false).unwrap_err();
        assert!(err.contains("search_budget_exceeded"));
        assert!(err.contains("ROI"));
    }

    #[test]
    fn tight_roi_is_within_budget() {
        let report = estimate_search_budget(
            1280,
            720,
            32,
            32,
            Some(SearchRoi {
                x: 100,
                y: 100,
                w: 80,
                h: 80,
            }),
        )
        .unwrap();
        assert!(report.within_budget());
        enforce_search_budget(&report, true).unwrap();
    }

    #[test]
    fn finds_exact_template_inside_roi() {
        let mut frame = solid_frame(40, 40, 10);
        let template = solid_frame(4, 4, 200);
        insert_template(&mut frame, &template, 12, 15);
        let matched = match_template_budgeted(
            &frame,
            &template,
            Some(SearchRoi {
                x: 8,
                y: 8,
                w: 20,
                h: 20,
            }),
            true,
            || Ok(()),
        )
        .unwrap();
        assert_eq!((matched.x, matched.y), (12, 15));
        assert!(matched.score > 0.99);
    }

    #[test]
    fn checkpoint_can_cancel_search() {
        let frame = solid_frame(64, 64, 255);
        let template = solid_frame(1, 1, 255);
        let mut checkpoints = 0;
        let err = match_template_budgeted(&frame, &template, None, false, || {
            checkpoints += 1;
            if checkpoints == 2 {
                Err("template search deadline exceeded".to_string())
            } else {
                Ok(())
            }
        })
        .unwrap_err();
        assert!(err.contains("deadline exceeded"));
        assert_eq!(checkpoints, 2);
    }

    #[test]
    fn match_only_without_template_is_fail_closed() {
        let (status, _detail, matched) = match_only_without_template_status();
        assert_eq!(status, "missing_template");
        assert!(!matched);
    }
}
