# macOS Compatibility TODO — NoWires QGIS Plugin

## CRITICAL

### 1. SharedMemory size exceeds macOS kern.sysv.shmmax default
**File:** `coverage_engine.py:310-316`

On macOS, `kern.sysv.shmmax` defaults to as low as 4 MB. Large DEM grids (e.g., 1024x1024 float32 = ~4 MB, or 3600x3600 = ~52 MB) exceed this, causing `OSError: [Errno 22] Invalid argument`. The existing `except OSError` fallback at line 514-524 degrades to sequential mode silently, but with no user-facing explanation.

**Fix:** Add a macOS-specific shared memory size check in `should_use_multiprocessing()`, or try creating a small test `SharedMemory` before committing to multiprocessing. Surface a clear message when falling back to sequential mode on macOS.

### 2. Shared memory segments leak on macOS when QGIS is force-quit
**File:** `coverage_engine.py:310-339`

On Linux, `/dev/shm` segments auto-cleanup on process exit. On macOS, POSIX shared memory (`shm_open`) persists until explicit `shm_unlink()` or system reboot. Force-quitting QGIS leaves orphaned segments that accumulate.

**Fix:** Register an `atexit` handler to clean up shared memory, or store segment names in a well-known location and clean up stale segments at plugin startup.

## HIGH

### 3. macOS "spawn" start method untested with SharedMemory
**File:** `coverage_engine.py:40-62, 87-91, 488-493`

macOS defaults to `"spawn"` for multiprocessing since Python 3.8. `_ensure_path()` (line 94-109) correctly patches `sys.path` for child processes, and `_init_cov_pool` correctly reinitializes globals. No correctness bug known, but performance is worse (full interpreter import per worker).

**Fix:** Consider explicitly setting `mp_context=mp.get_context("spawn")` in `ProcessPoolExecutor` to document the expectation. No functional change needed.

### 4. No macOS fallback for 3D view OpenGL/Metal issues
**File:** `three_d.py:148-157`

The 3D view function only checks for Windows (`sys.platform == "win32"`) and shows a Windows-specific message. On macOS, OpenGL is deprecated and Metal/MoltenVK can crash or render incorrectly. No try/except wraps the 3D canvas creation on macOS.

**Fix:** Add `sys.platform == "darwin"` check or wrap `createNewMapCanvas3D` in a try/except with a macOS-specific error message.

## MEDIUM

### 5. `os.rename()` not atomic across filesystems
**File:** `dem_downloader.py:201`, `worldcover_downloader.py:188`

`os.rename()` raises `OSError: Invalid cross-device link` if `TMPDIR` is on a different filesystem. `algorithm_contour.py:492` already uses `os.replace()`.

**Fix:** Replace `os.rename()` with `os.replace()` in both downloaders.

### 6. Multi-user cache collision in shared /tmp/NoWires
**File:** `dem_downloader.py:58-61`, `worldcover_downloader.py:57-60`

`os.makedirs(temp_dir, mode=0o700)` creates `/tmp/NoWires` owned by the first user with restrictive permissions. Subsequent users cannot write to it.

**Fix:** Include username in cache path (e.g., `/tmp/NoWires_<username>/`) or fall back to a user-specific temp directory on `PermissionError`.

### 7. No macOS-specific check in `should_use_multiprocessing()`
**File:** `coverage_engine.py:87-91`

Currently only blocks on Windows (`os.name == "nt"`). Should add a macOS-specific pre-check or at minimum log a clear message when shared memory creation fails.

**Fix:** Try creating a small test `SharedMemory` segment before committing to multiprocessing. On failure, log a macOS-specific message and fall back to sequential.

### 8. `CompositionMode_ColorDodge` renders differently on macOS Metal
**File:** `algorithm_contour.py:665-668`

Qt's `CompositionMode_ColorDodge` may render differently on macOS Metal backend vs. Linux/Windows OpenGL.

**Fix:** Cosmetic only — document the known rendering difference. No code change needed.

### 9. Matplotlib QtAgg + QDockWidget lifecycle on macOS
**File:** `algorithm_p2p.py:1143-1457`

`matplotlib.use("QtAgg")` with `QDockWidget` can cause rendering glitches or crashes on macOS if the dock is destroyed while matplotlib is connected.

**Fix:** The `_on_dock_destroyed` callback (line 1335-1337) calls `plt.close(fig)` which helps. Consider adding `matplotlib.use("MacOSX")` as fallback if QtAgg crashes on macOS.

### 10. Hardcoded temp filenames risk collision in concurrent instances
**File:** `algorithm_contour.py:256, 450, 503-505`

Files like `area_of_interest.shp` and `merged_contour.tif` use hardcoded names in a shared temp directory. Two concurrent QGIS instances will overwrite each other.

**Fix:** Use `tempfile.mkdtemp()`-based unique subdirectories (already partially done via `_temp_subdirs`, but some filenames are still hardcoded).

## LOW

### 11. CSV export missing `newline=""`
**File:** `algorithm_p2p.py:1311`

CSV export opens files with `open(path, "w")` without `newline=""`, inconsistent with `report_export.py:47` which uses the correct idiom.

**Fix:** Add `newline=""` to `open()` call.

### 12. Shapefile sidecar files may not be cleaned up
**File:** `algorithm_contour.py:284-291`

OGR creates `.shx`, `.dbf`, `.prj` sidecar files. Cleanup only tracks the primary `.shp`. On macOS APFS (case-sensitive), orphans may persist.

**Fix:** Use `OGR_Drivers` `DeleteDataSource` which removes all sidecars, or manually track and delete companion extensions.

### 13. `font-weight: 600` renders differently on macOS
**File:** `coverage_legend.py:63`

SemiBold weight maps differently on macOS San Francisco font.

**Fix:** Cosmetic only — no change needed.

### 14. `_ensure_path()` limited to plugin directory
**File:** `coverage_engine.py:94-109`

Only adds plugin dir to `sys.path`. If external dependencies are added later, macOS spawn-mode workers won't find them.

**Fix:** Consider adding `sys.path` entries for all current `sys.path` entries in the initializer, not just the plugin directory.