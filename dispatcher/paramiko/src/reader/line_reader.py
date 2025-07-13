class LineReader:
  def __init__(self, chan, prompt=""):
    self.chan = chan
    self.prompt = prompt
    self.buffer = []
    self.cursor_pos = 0
    self.escape_seq = b""
    self.prev_rendered_len = 0
    self.history = []
    self.history_index = -1

  def update_prompt(self, new_prompt):
    self.prompt = new_prompt

  def send_prompt(self):
    self.chan.send(self.prompt.encode("utf-8"))

  def redraw_buffer(self):
    self.chan.send(b"\r")
    self.send_prompt()

    rendered = (b"".join(self.buffer))
    self.chan.send(rendered)

    if self.prev_rendered_len > len(self.buffer):
      diff = self.prev_rendered_len - len(self.buffer)
      self.chan.send(b" " * diff)
      self.chan.send(f"\x1b[{diff}D".encode())

    back = len(rendered) - self.cursor_pos
    if back > 0:
      self.chan.send(f"\x1b[{back}D".encode())

    self.prev_rendered_len = len(self.buffer)

  def set_buffer_from_history(self):
    if 0 <= self.history_index < len(self.history):
      self.buffer = [c.encode("utf-8") for c in self.history[self.history_index]]
      self.cursor_pos = len(self.buffer)
      self.redraw_buffer()
      self.prev_rendered_len = len(self.buffer)
    else:
      print("Invalid history index")

  def handle_escape_sequence(self):
    try:
      seq = self.chan.recv(2)
    except Exception as e:
      print(f"Failed to read escape sequence: {e}")
      return

    # UP
    if seq == b"[A":
      if self.history:
        if self.history_index == -1:
          self.history_index = len(self.history) - 1
        else:
          if self.history_index > 0:
            self.history_index -= 1
        self.set_buffer_from_history()

    # DOWN
    elif seq == b"[B":
      if self.history and self.history_index < len(self.history) - 1:
        self.history_index += 1
        self.set_buffer_from_history()

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
        if t == b"~" and self.cursor_pos < len(self.buffer):
          del self.buffer[self.cursor_pos]
          if self.cursor_pos == len(self.buffer):
            self.chan.send(b" \b")
          else:
            remainder = b"".join(self.buffer[self.cursor_pos:]) + b" "
            self.chan.send(remainder)
            self.chan.send(f"\x1b[{len(remainder)}D".encode())
      except Exception as e:
        print(f"Failed to read escape sequence: {e}")
        return

  def read(self):
    self.buffer = []
    self.cursor_pos = 0
    self.history_index = -1
    self.chan.send(b"\r\x1b[2K")
    self.send_prompt()

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
            if self.cursor_pos == len(self.buffer):
              self.chan.send(b"\b \b")
            else:
              remainder = b"".join(self.buffer[self.cursor_pos:]) + b" "
              self.chan.send(b"\b" + remainder)
              self.chan.send(f"\x1b[{len(remainder)}D".encode())
          continue

        self.buffer.insert(self.cursor_pos, data)
        self.cursor_pos += 1

        if self.cursor_pos == len(self.buffer):
          self.chan.send(data)
        else:
          remainder = b"".join(self.buffer[self.cursor_pos - 1:])
          self.chan.send(remainder)
          self.chan.send(f"\x1b[{len(remainder) - 1}D".encode())

      except Exception:
        break

    return ""

  def cleanup_terminal(self):
    self.chan.send(b"\x1b[0m")