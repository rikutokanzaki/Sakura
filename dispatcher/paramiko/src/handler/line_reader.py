class LineReader:
  def __init__(self, chan, prompt=""):
    self.chan = chan
    self.prompt = prompt
    self.buffer = []
    self.cursor_pos = 0
    self.escape_seq = b""
    self.history = []
    self.history_index = -1

  def redraw_line(self):
    self.chan.send(b"\r\x1b[2K")

    self.chan.send(self.prompt.encode("utf-8"))
    self.chan.send(b"".join(self.buffer))

    back_steps = len(self.buffer) - self.cursor_pos
    if back_steps:
      self.chan.send(f"\x1b[{back_steps}D".encode("utf-8"))

  def set_buffer_from_history(self):
    print(f"Setting buffer from history index: {self.history_index}")
    if 0 <= self.history_index < len(self.history):
      self.buffer = [c.encode("utf-8") for c in self.history[self.history_index]]
      self.cursor_pos = len(self.buffer)
      print("Buffer from history:", self.buffer)
    else:
      print("Invalid history index")
    self.redraw_line()

  def handle_escape_sequence(self):
    try:
      seq = self.chan.recv(2)
    except Exception as e:
      print(f"Failed to read escape sequence: {e}")
      return

    # UP
    if seq == b"[A":
      print(f"[DEBUG] Before history_index handling: {self.history_index}, history length: {len(self.history)}")
      if self.history:
        if self.history_index == -1:
          self.history_index = len(self.history) - 1
        else:
          if self.history_index > 0:
            self.history_index -= 1
        self.set_buffer_from_history()
      print(f"[DEBUG] Escape sequence: {seq}, history_index: {self.history_index}")

    # DOWN
    elif seq == b"[B":
      if self.history and self.history_index < len(self.history) - 1:
        self.history_index += 1
        self.set_buffer_from_history()
      elif self.history_index == len(self.history) - 1:
        pass

    # RIGHT
    elif seq == b"[C":
      if self.cursor_pos < len(self.buffer):
        self.cursor_pos += 1
        self.chan.send(b"\x1b[C")

    # LEFT
    elif seq == b"[D":
      if self.cursor_pos > 0:
        self.cursor_pos -= 1
        self.chan.send(b"\x1b[D")

    # DELETE
    elif seq == b"[3":
      try:
        t = self.chan.recv(1)
      except Exception as e:
        print(f"Failed to read escape sequence: {e}")
        return

      if t == b"~" and self.cursor_pos < len(self.buffer):
        del self.buffer[self.cursor_pos]
        self.redraw_line()
        print("Current buffer:", b"".join(self.buffer))
  
  def cleanup_terminal(self):
    self.chan.send(b"\x1b[0m")

  def read(self):
    self.buffer = []
    self.cursor_pos = 0
    self.history_index = -1
    self.redraw_line()

    while True:
      try:
        data = self.chan.recv(1)
        if not data:
          break

        if data == b"\x1b":
          self.handle_escape_sequence()
          continue

        # ENTER
        if data in (b"\n", b"\r"):
          self.chan.send(b"\r\n")
          line = b"".join(self.buffer).decode("utf-8", errors="ignore")
          if line:
            self.history.append(line)
          return line

        # BACKSPACE
        if data in (b"\x7f", b"\x08"):
          if self.cursor_pos > 0:
            del self.buffer[self.cursor_pos - 1]
            self.cursor_pos -= 1
            self.redraw_line()
          continue

        self.buffer.insert(self.cursor_pos, data)
        self.cursor_pos += 1
        self.redraw_line()

      except Exception as e:
        break

    return ""
