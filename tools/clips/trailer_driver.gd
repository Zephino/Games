extends Node
## Scratch-only helper for recording trailers with Godot's Movie Maker.
## Replays timed input from the JSON file named by TRAILER_SCRIPT:
## [[frame, "click", x, y], [frame, "down", "D"], [frame, "up", "D"], [frame, "quit"],
##  [frame, "press", "Label"], [frame, "press_nth", "+", 2],
##  [frame, "auto", ["Continue", "Drive on"], period_frames], [frame, "spin", index, value]]

var _events: Array = []
var _frame := 0
var _release: Array = []
var _auto: Array = []
var _auto_period := 30

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var path := OS.get_environment("TRAILER_SCRIPT")
	if path != "":
		_events = JSON.parse_string(FileAccess.get_file_as_string(path))

func _process(_delta: float) -> void:
	_frame += 1
	for pos in _release:
		_mouse(pos, false)
	_release.clear()
	if not _auto.is_empty() and _frame % _auto_period == 0:
		for label in _auto:
			if _press(str(label), 0):
				break
	while not _events.is_empty() and int(_events[0][0]) <= _frame:
		var e: Array = _events.pop_front()
		match str(e[1]):
			"click":
				var p := Vector2(float(e[2]), float(e[3]))
				var m := InputEventMouseMotion.new()
				m.position = p
				m.global_position = p
				Input.parse_input_event(m)
				_mouse(p, true)
				_release.append(p)
			"down", "up":
				var k := InputEventKey.new()
				k.keycode = OS.find_keycode_from_string(str(e[2]))
				k.physical_keycode = k.keycode
				k.pressed = e[1] == "down"
				Input.parse_input_event(k)
			"press":
				_press(str(e[2]), 0)
			"press_nth":
				_press(str(e[2]), int(e[3]))
			"spin":
				var boxes: Array = []
				_collect_spins(get_tree().root, boxes)
				if int(e[2]) < boxes.size():
					(boxes[int(e[2])] as SpinBox).value = float(e[3])
			"bot":
				# Lastborn Colony only: let the game's own test bot make this turn's choices.
				var main := _find_with(get_tree().root, "refresh")
				if main != null and not (main.get("state") as Dictionary).is_empty():
					load(str(e[2])).act(main.state)
					main.refresh()
			"auto":
				_auto = e[2]
				_auto_period = int(e[3]) if e.size() > 3 else 30
			"quit":
				get_tree().quit()

## Presses the nth visible, enabled button (top to bottom) whose text contains label.
func _press(label: String, nth: int) -> bool:
	var found: Array = []
	_collect(get_tree().root, label.to_lower(), found)
	found.sort_custom(func(a, b): return a.global_position.y < b.global_position.y)
	if nth >= found.size():
		return false
	(found[nth] as BaseButton).emit_signal("pressed")
	return true

## "*" matches any button except ones that leave the game or open menus;
## "*mid" does the same but only for buttons in the middle half of the screen.
const SKIP := ["quit", "back", "setting", "leaderboard", "award", "suggest", "menu", "pause", "give up", "retry", "submit", "credits", "fullscreen", "install", "update"]

func _find_with(node: Node, method: String) -> Node:
	if node.has_method(method) and node.get("state") is Dictionary:
		return node
	for child in node.get_children():
		var hit := _find_with(child, method)
		if hit != null:
			return hit
	return null

func _collect_spins(node: Node, out: Array) -> void:
	if node is SpinBox and node.is_visible_in_tree():
		out.append(node)
	for child in node.get_children():
		_collect_spins(child, out)

func _collect(node: Node, label: String, out: Array) -> void:
	if node is Button and node.is_visible_in_tree() and not node.disabled:
		var text := str(node.text).to_lower()
		var ok := label in text
		if label == "*" or label == "*mid":
			ok = text.strip_edges() != "" and SKIP.all(func(w): return not w in text)
		if ok and label == "*mid":
			# Only buttons in the middle half of the screen (dialogs), not side panels.
			var width := (node as Control).get_viewport_rect().size.x
			var cx := (node as Control).get_global_rect().get_center().x
			ok = cx > width * 0.25 and cx < width * 0.75
		if ok:
			out.append(node)
	for child in node.get_children():
		_collect(child, label, out)

func _mouse(p: Vector2, pressed: bool) -> void:
	var b := InputEventMouseButton.new()
	b.button_index = MOUSE_BUTTON_LEFT
	b.position = p
	b.global_position = p
	b.pressed = pressed
	Input.parse_input_event(b)
