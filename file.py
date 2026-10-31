import os
import threading
import tkinter as messagebox
from tkinter import filedialog
import customtkinter as ctk
import yt_dlp

# Set up UI appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class VDJDownloaderApp(ctk.CTk):

  def __init__(self):
    super().__init__()
    self.search_cache = {}
    self.title("VirtualDJ yt-dlp Downloader")
    self.geometry("750x550")
    self.minsize(650, 450)

    # Default download folder (change this to your actual VirtualDJ music folder if desired)
    self.download_path = os.path.join(
        os.path.expanduser("~"), "Documents", "VirtualDJ", "Music"
    )
    if not os.path.exists(self.download_path):
      os.makedirs(self.download_path, exist_ok=True)

    # --- Top Frame: Search Bar & Path ---
    self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
    self.top_frame.pack(fill="x", padx=20, pady=15)

    self.search_entry = ctk.CTkEntry(
        self.top_frame,
        placeholder_text="Search track name or artist...",
        height=40,
        font=("Arial", 14),
    )
    self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    self.search_entry.bind("<Return>", lambda event: self.start_search())

    self.search_button = ctk.CTkButton(
        self.top_frame,
        text="Search",
        command=self.start_search,
        height=40,
        width=100,
    )
    self.search_button.pack(side="right")

    # --- Middle Frame: Results Box ---
    self.results_frame = ctk.CTkScrollableFrame(
        self, label_text="Search Results (Double-click or select to download)"
    )
    self.results_frame.pack(fill="both", expand=True, padx=20, pady=5)

    self.result_buttons = []

    # --- Bottom Frame: Status & Folder Config ---
    self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
    self.bottom_frame.pack(fill="x", padx=20, pady=15)

    self.status_label = ctk.CTkLabel(
        self.bottom_frame,
        text=f"Save Folder: {self.download_path}",
        text_color="gray",
        font=("Arial", 11),
    )
    self.status_label.pack(side="left", anchor="w")

    self.folder_button = ctk.CTkButton(
        self.bottom_frame,
        text="Change Folder",
        command=self.change_folder,
        width=110,
        height=28,
        fg_color="transparent",
        border_width=1,
    )
    self.folder_button.pack(side="right")

  def change_folder(self):
    chosen_dir = filedialog.askdirectory(initialdir=self.download_path)
    if chosen_dir:
      self.download_path = chosen_dir
      self.status_label.configure(text=f"Save Folder: {self.download_path}")

  def start_search(self):
    query = self.search_entry.get().strip()
    if not query:
      return

    self.search_button.configure(text="Searching...", state="disabled")
    # Run search in a separate thread to prevent freezing the UI
    threading.Thread(
        target=self.fetch_youtube_results, args=(query,), daemon=True
    ).start()

  def fetch_youtube_results(self, query):

    if query.lower() in self.search_cache:
        entries = self.search_cache[query.lower()]
        self.after(0, lambda: self.display_results(entries))
        return

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
        "ignoreerrors": True,
        "socket_timeout": 8,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch5:{query}",
                download=False
            )

        entries = [
            entry for entry in info.get("entries", [])
            if entry
        ]

        self.search_cache[query.lower()] = entries

        self.after(0, lambda: self.display_results(entries))

    except Exception as e:
        error_message = str(e)
        self.after(
            0,
            lambda msg=error_message:
            self.update_status_after_error(
                f"Search failed: {msg[:150]}"
            )
        )

  def display_results(self, entries):
    # Clear old buttons
    for btn in self.result_buttons:
      btn.destroy()
    self.result_buttons.clear()

    if not entries:
      lbl = ctk.CTkLabel(self.results_frame, text="No results found.")
      lbl.pack(pady=10)
      self.result_buttons.append(lbl)

    for entry in entries:
      title = entry.get("title", "Unknown Title")
      duration_sec = entry.get("duration", 0)
      minutes = int(duration_sec // 60)
      seconds = int(duration_sec % 60)
      duration_str = f"{minutes}:{seconds:02d}" if duration_sec else "N/A"
      url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"

      # Create a frame row for each search result
      row_frame = ctk.CTkFrame(self.results_frame, fg_color="transparent")
      row_frame.pack(fill="x", pady=2)

      title_lbl = ctk.CTkLabel(
          row_frame,
          text=f"[{duration_str}] {title}",
          anchor="w",
          font=("Arial", 13),
      )

      dl_btn = ctk.CTkButton(
          row_frame,
          text="Download to VDJ",
          width=120,
          height=28,
          command=lambda u=url, t=title: self.start_download(u, t),
      )
      dl_btn.pack(side="right", padx=5)
      dl_btn.pack_propagate(False)

      title_lbl.pack(side="left", fill="x", expand=True, padx=5)

      self.result_buttons.extend([row_frame, title_lbl, dl_btn])

    self.search_button.configure(text="Search", state="normal")

  def update_status_after_error(self, message):
    self.status_label.configure(text=message, text_color="red")
    self.search_button.configure(text="Search", state="normal")

  def start_download(self, url, title):
    self.status_label.configure(
        text=f"Downloading: {title[:40]}...", text_color="orange"
    )
    threading.Thread(
        target=self.download_audio, args=(url, title), daemon=True
    ).start()

  def download_audio(self, url, title):
    # Clean file name for filesystem safety
    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    output_template = os.path.join(self.download_path, f"%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }

    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

      self.after(
          0,
          lambda: self.status_label.configure(
              text=f"Saved to VDJ Folder! Drag & drop from sidebar.",
              text_color="green",
          ),
      )
    except Exception as e:
      error_message = str(e)

      self.after(
          0,
          lambda msg=error_message: self.status_label.configure(
              text=f"Download failed: {msg[:150]}",
              text_color="red"
          )
      )


if __name__ == "__main__":
  app = VDJDownloaderApp()
  app.mainloop()
