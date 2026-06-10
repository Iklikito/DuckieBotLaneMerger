extends PathFollow3D

@export var speed: float = 0.2
@export var loop_path: bool = true
@export var wait_progress: float = -1.0
@export var wait_duration: float = 0.0
var running: bool = true
var _has_waited: bool = false
var _wait_remaining: float = 0.0

func _ready() -> void:
	rotation_mode = PathFollow3D.ROTATION_Y
	loop = loop_path

func _process(delta: float) -> void:
	if running:
		if _wait_remaining > 0.0:
			_wait_remaining = max(0.0, _wait_remaining - delta)
			return
		if wait_progress >= 0.0 and not _has_waited and progress >= wait_progress:
			_has_waited = true
			_wait_remaining = wait_duration
			return
		progress += speed * delta
		if not loop_path and progress_ratio >= 1.0:
			running = false
