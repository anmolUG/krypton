"""
Gradio Demo Application — Professional Monochrome Edition
========================================================
Persistent enrollment: reference photos are saved to
  data/enrollment/<student_id>/*.jpg
and auto-loaded every time the app starts.

Compatible with Gradio 6.0+ (theme/css passed to launch()).
"""

import sys
import cv2
import numpy as np
import gradio as gr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detection import load_config
from src.matching import GalleryMatcher
from src.enrollment import EnrollmentManager
from src.pipeline import AttendancePipeline


# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
ENROLLMENT_DIR = Path("data/enrollment")
GALLERY_DIR    = Path("data/gallery")

for d in [ENROLLMENT_DIR, GALLERY_DIR, Path("data/output")]:
    d.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────
# Disk helpers
# ──────────────────────────────────────────────────────────────────────
def _save_images_to_disk(student_id: str, bgr_images: list[np.ndarray]) -> list[Path]:
    """Append BGR images to data/enrollment/<student_id>/ and return saved paths."""
    student_dir = ENROLLMENT_DIR / student_id
    student_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(student_dir.glob("img_*.jpg"))
    start_idx = len(existing)
    saved = []
    for i, img in enumerate(bgr_images):
        fname = student_dir / f"img_{start_idx + i:03d}.jpg"
        cv2.imwrite(str(fname), img)
        saved.append(fname)
    return saved


def _load_images_from_disk(student_id: str) -> list[np.ndarray]:
    """Load all BGR images stored for a student."""
    student_dir = ENROLLMENT_DIR / student_id
    if not student_dir.exists():
        return []
    imgs = []
    for p in sorted(student_dir.glob("img_*.jpg")):
        img = cv2.imread(str(p))
        if img is not None:
            imgs.append(img)
    return imgs


def _delete_image_from_disk(student_id: str, img_index: int):
    """Delete one image file and rename remaining so indices stay gapless."""
    student_dir = ENROLLMENT_DIR / student_id
    files = sorted(student_dir.glob("img_*.jpg"))
    if img_index < 0 or img_index >= len(files):
        return
    files[img_index].unlink()
    # Rename remaining to close the gap
    remaining = sorted(student_dir.glob("img_*.jpg"))
    for i, f in enumerate(remaining):
        target = student_dir / f"img_{i:03d}.jpg"
        if f != target:
            f.rename(target)


def _student_folders() -> list[str]:
    """Return sorted list of student_ids that have folders on disk."""
    return sorted([d.name for d in ENROLLMENT_DIR.iterdir() if d.is_dir()])


def _read_name_meta(student_id: str) -> str:
    """Read display name from a meta file, fall back to student_id."""
    meta = ENROLLMENT_DIR / student_id / ".name"
    if meta.exists():
        return meta.read_text().strip()
    return student_id.replace("_", " ").title()


def _write_name_meta(student_id: str, name: str):
    meta = ENROLLMENT_DIR / student_id / ".name"
    meta.write_text(name)


# ──────────────────────────────────────────────────────────────────────
# Global state — initialise once, persists across Gradio calls
# ──────────────────────────────────────────────────────────────────────
CONFIG             = load_config()
enrollment_manager = EnrollmentManager(CONFIG)
pipeline           = AttendancePipeline()

staged_images: list[np.ndarray] = []   # BGR, temporary staging buffer


def _rebuild_pipeline_gallery():
    """Sync pipeline matcher from whatever is in enrollment_manager."""
    if enrollment_manager.gallery:
        enrollment_manager.save_gallery()
    pipeline.set_matcher(enrollment_manager.matcher)


# ── Auto-load all students from disk on startup ──────────────────────
def _bootstrap():
    """Re-enroll every student found in data/enrollment/ at startup."""
    folders = _student_folders()
    if not folders:
        return
    for student_id in folders:
        imgs = _load_images_from_disk(student_id)
        if not imgs:
            continue
        name = _read_name_meta(student_id)
        enrollment_manager.enroll_student(student_id, name, images=imgs)

    if enrollment_manager.gallery:
        enrollment_manager.matcher.build_index(enrollment_manager.gallery)
        _rebuild_pipeline_gallery()
    print(f"[startup] Loaded {len(folders)} student(s) from disk.")


_bootstrap()


# ──────────────────────────────────────────────────────────────────────
# Enrolled-table helper
# ──────────────────────────────────────────────────────────────────────
def _get_enrolled_rows():
    rows = []
    for sid in _student_folders():
        name = _read_name_meta(sid)
        count = len(list((ENROLLMENT_DIR / sid).glob("img_*.jpg")))
        rows.append([name, sid, str(count)])
    if not rows:
        rows = [["No students enrolled yet", "", ""]]
    return rows


def _student_name_choices():
    return [_read_name_meta(sid) for sid in _student_folders()]


# ──────────────────────────────────────────────────────────────────────
# Staging (Enrollment tab)
# ──────────────────────────────────────────────────────────────────────
def _staged_preview():
    return [cv2.cvtColor(img, cv2.COLOR_BGR2RGB) for img in staged_images]


def stage_image(image_input):
    if image_input is None:
        return f"No image received. Queue: {len(staged_images)}", _staged_preview()
    if isinstance(image_input, np.ndarray):
        staged_images.append(cv2.cvtColor(image_input, cv2.COLOR_RGB2BGR))
    return f"{len(staged_images)} image(s) in queue.", _staged_preview()


def clear_staged():
    staged_images.clear()
    return "Queue cleared.", _staged_preview()


def enroll_student(student_name: str):
    if not student_name or not student_name.strip():
        return "ERROR: Enter a student name.", _get_enrolled_rows()
    if not staged_images:
        return "ERROR: Add at least one image to the queue first.", _get_enrolled_rows()

    student_name = student_name.strip()
    student_id   = student_name.replace(" ", "_").lower()

    # Save images to disk first
    _save_images_to_disk(student_id, staged_images)
    _write_name_meta(student_id, student_name)

    # Re-enroll from the full disk set (merge with any existing images)
    all_imgs = _load_images_from_disk(student_id)
    result = enrollment_manager.enroll_student(student_id, student_name, images=all_imgs)

    if result["success"]:
        enrollment_manager.matcher.build_index(enrollment_manager.gallery)
        _rebuild_pipeline_gallery()
        staged_images.clear()
        return f"SUCCESS: {result['message']}", _get_enrolled_rows()
    else:
        return f"FAILURE: {result['message']}", _get_enrolled_rows()


def reset_all():
    global enrollment_manager
    import shutil
    enrollment_manager = EnrollmentManager(CONFIG)
    pipeline.set_matcher(GalleryMatcher(CONFIG))
    staged_images.clear()
    if ENROLLMENT_DIR.exists():
        shutil.rmtree(str(ENROLLMENT_DIR))
    ENROLLMENT_DIR.mkdir(parents=True, exist_ok=True)
    if GALLERY_DIR.exists():
        shutil.rmtree(str(GALLERY_DIR))
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    return "STATUS: Registry wiped.", _get_enrolled_rows()


# ──────────────────────────────────────────────────────────────────────
# Manage tab helpers
# ──────────────────────────────────────────────────────────────────────
def load_student_images(student_display_name: str):
    """Load images for the selected student (for Manage tab gallery)."""
    if not student_display_name:
        return [], "Select a student above."
    # Find student_id by matching display name
    sid = _name_to_id(student_display_name)
    if sid is None:
        return [], "Student not found."
        
    student_dir = ENROLLMENT_DIR / sid
    if not student_dir.exists():
        return [], f"0 image(s) stored for {student_display_name}."
        
    # In Gradio, passing absolute filepaths to a Gallery is much faster and 
    # more reliable than passing raw numpy arrays over the websocket.
    img_paths = [str(p.absolute()) for p in sorted(student_dir.glob("img_*.jpg"))]
    return img_paths, f"{len(img_paths)} image(s) stored for {student_display_name}."


def _name_to_id(display_name: str):
    for sid in _student_folders():
        if _read_name_meta(sid) == display_name:
            return sid
    return None


def add_images_to_student(student_display_name: str, image_input):
    """Add one more image to an existing student."""
    empty_res = "ERROR: Select a student first.", [], gr.update(), _get_enrolled_rows(), _get_enrolled_rows()
    if not student_display_name:
        return "ERROR: Select a student first.", [], gr.update(), _get_enrolled_rows(), _get_enrolled_rows()
    if image_input is None:
        return "ERROR: No image provided.", [], gr.update(), _get_enrolled_rows(), _get_enrolled_rows()

    sid = _name_to_id(student_display_name)
    if sid is None:
        return "ERROR: Student not found.", [], gr.update(), _get_enrolled_rows(), _get_enrolled_rows()

    bgr = cv2.cvtColor(image_input, cv2.COLOR_RGB2BGR)
    _save_images_to_disk(sid, [bgr])

    # Re-compute embedding from updated image set
    all_imgs = _load_images_from_disk(sid)
    name = _read_name_meta(sid)
    enrollment_manager.enroll_student(sid, name, images=all_imgs)
    enrollment_manager.matcher.build_index(enrollment_manager.gallery)
    _rebuild_pipeline_gallery()

    imgs, status = load_student_images(student_display_name)
    return f"SUCCESS: Image added. {status}", imgs, gr.update(choices=_student_name_choices()), _get_enrolled_rows(), _get_enrolled_rows()


def delete_student_image(student_display_name: str, selected_idx: int):
    """Delete image at selected_idx for the given student."""
    if not student_display_name:
        return "ERROR: Select a student first.", load_student_images(student_display_name)[0], _get_enrolled_rows(), _get_enrolled_rows()
    sid = _name_to_id(student_display_name)
    if sid is None:
        return "ERROR: Student not found.", [], _get_enrolled_rows(), _get_enrolled_rows()
    if selected_idx is None or selected_idx < 0:
        return "ERROR: Click an image in the gallery first to select it.", \
               load_student_images(student_display_name)[0], _get_enrolled_rows(), _get_enrolled_rows()

    _delete_image_from_disk(sid, selected_idx)

    # Re-compute embedding from remaining images
    all_imgs = _load_images_from_disk(sid)
    if all_imgs:
        name = _read_name_meta(sid)
        enrollment_manager.enroll_student(sid, name, images=all_imgs)
        enrollment_manager.matcher.build_index(enrollment_manager.gallery)
    else:
        # If last image is deleted, wipe the student from the registry
        import shutil
        shutil.rmtree(str(ENROLLMENT_DIR / sid), ignore_errors=True)
        enrollment_manager.gallery.pop(sid, None)
        if enrollment_manager.gallery:
            enrollment_manager.matcher.build_index(enrollment_manager.gallery)
        else:
            enrollment_manager.matcher.index = None

    _rebuild_pipeline_gallery()

    imgs, status = load_student_images(student_display_name)
    return f"SUCCESS: Image deleted. {status}", imgs, _get_enrolled_rows(), _get_enrolled_rows()


def delete_student_entirely(student_display_name: str):
    """Remove a student from the registry completely."""
    if not student_display_name:
        return "ERROR: Select a student first.", [], gr.update(choices=_student_name_choices()), _get_enrolled_rows(), _get_enrolled_rows()
    sid = _name_to_id(student_display_name)
    if sid is None:
        return "ERROR: Student not found.", [], gr.update(choices=_student_name_choices()), _get_enrolled_rows(), _get_enrolled_rows()

    import shutil
    shutil.rmtree(str(ENROLLMENT_DIR / sid), ignore_errors=True)

    # Remove from in-memory gallery and rebuild
    enrollment_manager.gallery.pop(sid, None)
    if enrollment_manager.gallery:
        enrollment_manager.matcher.build_index(enrollment_manager.gallery)
        _rebuild_pipeline_gallery()
    else:
        enrollment_manager.matcher.index = None
        pipeline.set_matcher(GalleryMatcher(CONFIG))

    return (
        f"SUCCESS: {student_display_name} removed from registry.",
        [],
        gr.update(choices=_student_name_choices(), value=None),
        _get_enrolled_rows(),
        _get_enrolled_rows(),
    )


# ──────────────────────────────────────────────────────────────────────
# Attendance
# ──────────────────────────────────────────────────────────────────────
def process_classroom_photo(image):
    if image is None:
        return None, [["No image provided", "", "", ""]], ""
    if not pipeline._gallery_loaded:
        return None, [["Enroll students first", "", "", ""]], ""

    bgr    = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    result = pipeline.process_image(image=bgr)
    out    = cv2.cvtColor(result["annotated_image"], cv2.COLOR_BGR2RGB)

    attendance = result["attendance"]
    rows = []
    for e in attendance.get("attendance", []):
        if   e["status"] == "TENTATIVE":  status = "TENTATIVE"
        elif e["status"] == "AMBIGUOUS":  status = "AMBIGUOUS"
        elif e["present"]:                status = "PRESENT"
        else:                             status = "ABSENT"
        pos = f"R{e['row']}, C{e.get('column','?')}" if e.get("row") else ""
        rows.append([e["student_name"], status,
                     f"{e['confidence']:.2f}" if e["confidence"] > 0 else "0.00", pos])

    for uf in attendance.get("unidentified_faces", []):
        loc = uf.get("location", {})
        pos = f"R{loc['row']}, C{loc.get('column','?')}" if loc.get("row") else ""
        rows.append([uf["label"], "UNKNOWN", f"{uf['best_match_score']:.2f}", pos])

    if not rows:
        rows = [["No faces detected", "", "", ""]]

    s = attendance.get("summary", {})
    summary = (f"Detected: {s.get('total_detected_faces',0)} | "
               f"Present: {s.get('present_count',0)}/{s.get('total_enrolled',0)} | "
               f"Unknown: {s.get('unknown_faces_count',0)}")

    return out, rows, summary


# ──────────────────────────────────────────────────────────────────────
# Theme & CSS  (Gradio 6 — pass to launch())
# ──────────────────────────────────────────────────────────────────────
mono_theme = gr.themes.Base(
    primary_hue="slate", secondary_hue="slate", neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
).set(
    body_background_fill="*neutral_950",
    body_text_color="*neutral_200",
    block_background_fill="*neutral_900",
    block_border_color="*neutral_800",
    block_title_text_color="*neutral_100",
    button_primary_background_fill="*neutral_100",
    button_primary_text_color="*neutral_950",
    button_primary_background_fill_hover="*neutral_300",
    button_secondary_background_fill="*neutral_800",
    button_secondary_text_color="*neutral_100",
    button_secondary_background_fill_hover="*neutral_700",
    input_background_fill="*neutral_950",
    input_border_color="*neutral_800",
    table_border_color="*neutral_800",
    table_even_background_fill="*neutral_900",
    table_odd_background_fill="*neutral_950",
)

custom_css = """
.gradio-container { background-color: #0a0a0a !important; max-width: 1280px !important; }
footer, .built-with { display: none !important; }
button[title*='Share'], button[aria-label*='Share'] { display: none !important; }
table { border-collapse: collapse !important; }
th { text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em;
     color: #737373 !important; border-bottom: 1px solid #262626 !important; }
"""


# ──────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────
def create_app():
    # A sleek minimalist slate diamond for the tab favicon
    krypton_logo = "<link rel='icon' type='image/svg+xml' href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><polygon points='50,10 90,50 50,90 10,50' fill='%2364748b'/></svg>\">"
    
    with gr.Blocks(title="Krypton", head=krypton_logo) as app:
        with gr.Tabs():

            # ── 1. Enrollment ────────────────────────────────────────
            with gr.TabItem("Enrollment"):
                gr.Markdown("Register a new student. Images are saved to disk and loaded automatically on next startup.")
                with gr.Row():
                    with gr.Column(scale=1):
                        name_input  = gr.Textbox(label="Full Name", placeholder="John Doe")
                        paste_input = gr.Image(
                            label="Paste / Upload Image  (Ctrl+V or drag-drop)",
                            type="numpy", sources=["upload", "clipboard"], height=200,
                        )
                        with gr.Row():
                            add_btn   = gr.Button("Add to Queue", variant="secondary", size="sm")
                            clr_btn   = gr.Button("Clear Queue",  variant="secondary", size="sm")
                        queue_status  = gr.Textbox(label="Queue", value="0 image(s).", interactive=False)
                        staged_gallery = gr.Gallery(
                            label="Queued Images", columns=5, height=120, interactive=False,
                        )
                        with gr.Row():
                            enroll_btn = gr.Button("Enroll Student", variant="primary")
                            reset_btn  = gr.Button("Wipe Registry",  variant="secondary")
                        enroll_status = gr.Textbox(label="Status", interactive=False)

                    with gr.Column(scale=1):
                        enrolled_table = gr.Dataframe(
                            headers=["Name", "ID", "Stored Images"],
                            value=_get_enrolled_rows(), label="Registry", interactive=False,
                        )

                add_btn.click(stage_image, [paste_input], [queue_status, staged_gallery])
                clr_btn.click(clear_staged, [], [queue_status, staged_gallery])
                enroll_btn.click(
                    enroll_student, [name_input], [enroll_status, enrolled_table]
                )
                
                reset_btn.click(reset_all, [], [enroll_status, enrolled_table])

            # ── 2. Manage ────────────────────────────────────────────
            with gr.TabItem("Manage Students"):
                gr.Markdown(
                    "Select an enrolled student to view, add, or delete their reference images. "
                    "Changes take effect immediately — the recognition model updates on the fly."
                )
                student_dd = gr.Dropdown(
                    label="Select Student",
                    choices=_student_name_choices(),
                    interactive=True,
                )
                manage_status = gr.Textbox(label="Status", interactive=False)

                manage_gallery = gr.Gallery(
                    label="Stored Reference Images  (click one to select it before deleting)",
                    columns=6, height=220, interactive=False,
                )

                with gr.Row():
                    add_img_input = gr.Image(
                        label="Add Image  (Ctrl+V or drag-drop)",
                        type="numpy", sources=["upload", "clipboard"], height=180,
                    )
                    with gr.Column():
                        add_img_btn = gr.Button("Add Image to Student", variant="primary")
                        del_img_btn = gr.Button("Delete Selected Image", variant="secondary")
                        del_stu_btn = gr.Button("Remove Student Entirely", variant="secondary")

                manage_enrolled_table = gr.Dataframe(
                    headers=["Name", "ID", "Stored Images"],
                    value=_get_enrolled_rows(), label="Updated Registry", interactive=False,
                )

                # State to hold selected image index (set by clicking gallery)
                selected_img_idx = gr.State(value=-1)

                def _capture_selected(evt: gr.SelectData):
                    return evt.index

                # Load images when student selected (use .select which fires on user interaction)
                student_dd.select(
                    load_student_images, [student_dd], [manage_gallery, manage_status]
                )
                # Capture which image was clicked
                manage_gallery.select(
                    _capture_selected, None, selected_img_idx
                )
                # Add image — updates gallery, dropdown, and both registry tables
                add_img_btn.click(
                    add_images_to_student,
                    [student_dd, add_img_input],
                    [manage_status, manage_gallery, student_dd, manage_enrolled_table, enrolled_table],
                )
                # Delete selected image — updates gallery and both registry tables
                del_img_btn.click(
                    delete_student_image,
                    [student_dd, selected_img_idx],
                    [manage_status, manage_gallery, manage_enrolled_table, enrolled_table],
                )
                # Delete whole student
                del_stu_btn.click(
                    delete_student_entirely,
                    [student_dd],
                    [manage_status, manage_gallery, student_dd, manage_enrolled_table, enrolled_table],
                )

            # ── 3. Attendance ─────────────────────────────────────────
            with gr.TabItem("Attendance"):
                gr.Markdown("Paste or upload a classroom photo to run attendance analysis.")
                with gr.Row():
                    with gr.Column(scale=1):
                        classroom_input = gr.Image(
                            label="Classroom Photo  (Ctrl+V or drag-drop)",
                            type="numpy", sources=["upload", "clipboard"],
                        )
                        process_btn = gr.Button("Run Analysis", variant="primary", size="lg")
                    with gr.Column(scale=1):
                        annotated_output = gr.Image(
                            label="Annotated Result", type="numpy",
                        )

                summary_output = gr.Textbox(label="Summary", interactive=False)
                attendance_table = gr.Dataframe(
                    headers=["Student", "Status", "Confidence", "Position"],
                    label="Attendance Log", interactive=False,
                )
                process_btn.click(
                    process_classroom_photo,
                    [classroom_input],
                    [annotated_output, attendance_table, summary_output],
                )

    return app


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="127.0.0.1",
        share=False,
        show_error=True,
        theme=mono_theme,
        css=custom_css,
    )
