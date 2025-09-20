import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox
from tkinter import simpledialog
import json
import os
import pyperclip
import keyboard
import time
import sys
import pyautogui
# ★★★ 新增导入 ★★★
from PIL import Image
import pystray
import threading
import base64
import io

# ★★★ 新增：为托盘图标嵌入一个默认图标（Base64编码），避免依赖外部文件 ★★★
ICON_B64 = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAACYSURBVDhPzZELCsAwCEPbvES8S38ETyBNLoI32AOr4An4K2gQPIC99s5w4A6Eg72YYDIy+AMB+D8/QosgpddBvB5dfat2FRZyQ2y5lGRCwGSsylLh4n5t2JqfRVd4aR4H60yp112gGkFfDXIAR84PAe7iCN3A8sAaAHLv2s83sQ4A8s/d4DIF4ECINsB+6AF5GCkQk8A54U8A49ILwFcDtAFb4AQA/xFN4Bqg7wAAAABJRU5ErkJggg=='


class Tooltip:
    def __init__(self, widget, text, bootstyle="info-inverse"):
        self.widget = widget
        max_chars = 32
        display_text = text
        if len(text) > max_chars:
            display_text = text[:max_chars] + "..."
        self.text = display_text
        self.bootstyle = bootstyle
        self.tooltip_window = None
        self.after_id = None
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.schedule_hide)

    def schedule_show(self, event):
        self.after_id = self.widget.after(500, self.show_tooltip)

    def schedule_hide(self, event):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide_tooltip()

    def show_tooltip(self):
        if self.tooltip_window or not self.text:
            return
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        style = ttk.Style.get_instance()
        color_name = self.bootstyle.split('-')[0]
        bg_color = style.colors.get(color_name)
        fg_color = style.colors.light if 'inverse' in self.bootstyle else style.colors.dark
        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background=bg_color, foreground=fg_color, relief='solid', borderwidth=1,
                         font=("Microsoft YaHei", 10, "normal"), padx=8, pady=18)
        label.pack(ipadx=1)
        self.tooltip_window.update_idletasks()
        tooltip_width = self.tooltip_window.winfo_width()
        tooltip_height = self.tooltip_window.winfo_height()
        main_window = self.widget.winfo_toplevel()
        main_window_x = main_window.winfo_rootx()
        button_y = self.widget.winfo_rooty()
        button_height = self.widget.winfo_height()
        final_x = main_window_x - tooltip_width - 5
        final_y = button_y + (button_height // 2) - (tooltip_height // 2)
        self.tooltip_window.wm_geometry(f"+{final_x}+{final_y}")

    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

DATA_FILE = "snippets.json"

class SnippetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("阿尔托莉雅潘德拉贡")
        window_width = 450
        window_height = 500
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_position = screen_width - window_width
        y_position = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.attributes('-alpha', 0.75)

        style = ttk.Style()
        new_font_family = "Microsoft YaHei"
        style.configure('TButton', padding=(20, 18), font=(new_font_family, 11))
        style.configure('Outline.TButton', padding=(20, 18), font=(new_font_family, 11))
        style.configure('TLabel', font=(new_font_family, 10))
        style.configure('TEntry', font=(new_font_family, 10))
        info_color = style.colors.get('info')
        style.configure('Custom.info.Outline.TButton',
                        padding=(20, 18),
                        font=(new_font_family, 12, "bold"),
                        foreground="white",
                        bordercolor=info_color)
        style.configure('Transparent.TLabel', foreground="#CCCCCC")

        self.profiles = self.load_profiles()
        self.current_profile_name = next(iter(self.profiles))
        self.is_edit_mode = False
        self._current_view = None
        self._editing_snippet_original_title = None
        self.icon = None

        self.setup_hotkey()
        self.create_base_widgets()
        self.create_views()
        self.show_view("home")
        self.refresh_ui()

        self.root.bind("<MouseWheel>", self._on_mousewheel)
        self.root.bind("<Button-4>", self._on_mousewheel)
        self.root.bind("<Button-5>", self._on_mousewheel)

    # ★★★ 核心改动：修改创建托盘图标的方式 ★★★
    def setup_tray_icon(self):
        # 1. 定义一个函数，该函数在被调用时才创建并返回图像对象
        def create_image():
            icon_data = base64.b64decode(ICON_B64)
            return Image.open(io.BytesIO(icon_data))

        # 2. 定义菜单项
        menu = (pystray.MenuItem('显示', self.show_window, default=True),
                pystray.MenuItem('退出', self.quit_app))

        # 3. 将 create_image 函数作为 icon 参数传递，而不是直接传递图像对象
        self.icon = pystray.Icon(
            "SnippetApp",
            icon=create_image,  # <-- 注意这里的变化
            title="代码片段工具",
            menu=menu)

        # 4. 在后台守护线程中运行图标，这样它就不会阻塞Tkinter的主循环
        threading.Thread(target=self.icon.run, daemon=True).start()


    def show_window(self):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.focus_force)
        self.root.after(0, self.root.attributes, '-topmost', True)

    def hide_window(self):
        self.root.withdraw()

    def quit_app(self):
        self.icon.stop()
        self.root.after(0, self.on_closing)

    def create_base_widgets(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.navbar = ttk.Frame(self.root, padding=(20, 10, 20, 0))
        self.navbar.grid(row=0, column=0, sticky="ew")
        self.navbar.grid_columnconfigure(0, weight=1)
        self.navbar.grid_columnconfigure(1, weight=1)
        self.switch_profile_button = ttk.Button(self.navbar, text="切换方案", command=self.go_to_profiles_view, bootstyle="info-outline")
        self.switch_profile_button.grid(row=0, column=0, sticky="ew", padx=(0, 1))
        self.edit_button = ttk.Button(self.navbar, text="编辑", command=self.toggle_edit_mode, bootstyle="secondary-outline")
        self.edit_button.grid(row=0, column=1, sticky="ew")
        self.delete_profile_button = ttk.Button(self.navbar, text="删除当前方案", command=self.delete_current_profile, bootstyle="danger-outline")

    def create_views(self):
        self.main_container = ttk.Frame(self.root)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        new_font_family = "Microsoft YaHei"

        self.bottom_bar = ttk.Frame(self.main_container)
        self.bottom_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.bottom_bar.grid_columnconfigure(0, weight=1)
        self.add_snippet_btn = ttk.Button(self.bottom_bar, text="✚", command=self.go_to_add_view, bootstyle="success-outline")
        self.add_snippet_btn.grid(row=0, column=0, sticky="ew")

        self.home_view = ttk.Frame(self.main_container)
        self.home_view.grid_columnconfigure(0, weight=1)
        self.home_view.grid_rowconfigure(1, weight=1)
        self.profile_name_label = ttk.Label(self.home_view, text="", font=(new_font_family, 16, "bold"), style='Transparent.TLabel', anchor="center")
        self.profile_name_label.grid(row=0, column=0, pady=(0, 10), sticky="ew", padx=10)
        self.scrollable_frame_container = ttk.Frame(self.home_view)
        self.scrollable_frame_container.grid(row=1, column=0, sticky="nsew", padx=10)
        self.scrollable_frame_container.grid_rowconfigure(0, weight=1)
        self.scrollable_frame_container.grid_columnconfigure(0, weight=1)
        self.home_canvas = tk.Canvas(self.scrollable_frame_container, highlightthickness=0, bg=self.root.cget('bg'))
        scrollbar = ttk.Scrollbar(self.scrollable_frame_container, orient="vertical", command=self.home_canvas.yview, bootstyle="round")
        self.scrollable_frame = ttk.Frame(self.home_canvas)
        canvas_frame_id = self.home_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.home_canvas.configure(yscrollcommand=scrollbar.set)
        self.home_canvas.bind("<Configure>", lambda e: self.home_canvas.itemconfig(canvas_frame_id, width=e.width))
        self.scrollable_frame.bind("<Configure>", lambda e: self.home_canvas.configure(scrollregion=self.home_canvas.bbox("all")))
        self.home_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.edit_view = ttk.Frame(self.main_container, padding=10)
        self.edit_view.grid_columnconfigure(0, weight=1)
        self.edit_view_label = ttk.Label(self.edit_view, text="编辑片段", font=(new_font_family, 16, "bold"))
        self.edit_view_label.grid(row=0, column=0, pady=(0, 20), sticky="w")
        ttk.Label(self.edit_view, text="标题:").grid(row=1, column=0, sticky="w", padx=5)
        self.snippet_title_entry = ttk.Entry(self.edit_view)
        self.snippet_title_entry.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 10))
        ttk.Label(self.edit_view, text="内容:").grid(row=3, column=0, sticky="w", padx=5)
        self.snippet_content_textbox = ttk.Text(self.edit_view, height=10, font=(new_font_family, 11))
        self.snippet_content_textbox.grid(row=4, column=0, sticky="nsew", padx=5, pady=(0, 20))
        self.edit_view.grid_rowconfigure(4, weight=1)
        edit_view_buttons_frame = ttk.Frame(self.edit_view)
        edit_view_buttons_frame.grid(row=5, column=0, sticky="ew")
        edit_view_buttons_frame.grid_columnconfigure(0, weight=1)
        self.save_button = ttk.Button(edit_view_buttons_frame, text="保存", command=self.save_snippet, bootstyle="success-outline")
        self.save_button.grid(row=0, column=1, padx=(0,5))
        self.cancel_button = ttk.Button(edit_view_buttons_frame, text="取消", command=lambda: self.show_view("home"), bootstyle="secondary-outline")
        self.cancel_button.grid(row=0, column=2)

        self.profiles_view = ttk.Frame(self.main_container, padding=10)
        self.profiles_view.grid_columnconfigure(0, weight=1)
        self.profiles_view.grid_rowconfigure(1, weight=1)
        profiles_view_header = ttk.Frame(self.profiles_view)
        profiles_view_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        profiles_view_header.grid_columnconfigure(1, weight=1)
        back_button = ttk.Button(profiles_view_header, text="<", width=4, command=lambda: self.show_view("home"), bootstyle="secondary-outline")
        back_button.grid(row=0, column=0, sticky="w")
        add_profile_btn = ttk.Button(profiles_view_header, text="✚", command=self.add_new_profile, bootstyle="success-outline")
        add_profile_btn.grid(row=0, column=2, sticky="e")
        prof_scroll_container = ttk.Frame(self.profiles_view)
        prof_scroll_container.grid(row=1, column=0, sticky="nsew")
        prof_scroll_container.grid_rowconfigure(0, weight=1)
        prof_scroll_container.grid_columnconfigure(0, weight=1)
        self.profiles_canvas = tk.Canvas(prof_scroll_container, highlightthickness=0, bg=self.root.cget('bg'))
        prof_scrollbar = ttk.Scrollbar(prof_scroll_container, orient="vertical", command=self.profiles_canvas.yview, bootstyle="round")
        self.profiles_scrollable_frame = ttk.Frame(self.profiles_canvas)
        prof_canvas_frame_id = self.profiles_canvas.create_window((0, 0), window=self.profiles_scrollable_frame, anchor="nw")
        self.profiles_canvas.configure(yscrollcommand=prof_scrollbar.set)
        self.profiles_canvas.bind("<Configure>", lambda e: self.profiles_canvas.itemconfig(prof_canvas_frame_id, width=e.width))
        self.profiles_scrollable_frame.bind("<Configure>", lambda e: self.profiles_canvas.configure(scrollregion=self.profiles_canvas.bbox("all")))
        self.profiles_canvas.grid(row=0, column=0, sticky="nsew")
        prof_scrollbar.grid(row=0, column=1, sticky="ns")

    def _on_mousewheel(self, event):
        canvas_to_scroll = None
        if self._current_view == self.home_view:
            canvas_to_scroll = self.home_canvas
        elif self._current_view == self.profiles_view:
            canvas_to_scroll = self.profiles_canvas
        if canvas_to_scroll:
            if hasattr(event, 'delta') and event.delta != 0:
                canvas_to_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 5:
                canvas_to_scroll.yview_scroll(1, "units")
            elif event.num == 4:
                canvas_to_scroll.yview_scroll(-1, "units")

    def populate_snippets(self):
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.scrollable_frame.update_idletasks()
        current_snippets = self.profiles.get(self.current_profile_name, {})
        for title in sorted(current_snippets.keys()):
            content = current_snippets[title]
            item_frame = ttk.Frame(self.scrollable_frame)
            item_frame.pack(fill="x", expand=True, pady=(0, 5), padx=2)
            item_frame.grid_columnconfigure(0, weight=1)
            if not self.is_edit_mode:
                main_button = ttk.Button(item_frame, text=title, command=lambda c=content: self.paste_snippet(c), style="Custom.info.Outline.TButton")
                main_button.grid(row=0, column=0, columnspan=3, sticky="ew")
                if content:
                    Tooltip(main_button, text=content, bootstyle="info-inverse")
            else:
                title_display_button = ttk.Button(item_frame, text=title, bootstyle="secondary", state="disabled")
                title_display_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
                edit_s_button = ttk.Button(item_frame, text="编辑", width=6, command=lambda t=title: self.go_to_edit_view(t), bootstyle="warning-outline")
                edit_s_button.grid(row=0, column=1, padx=(0, 5))
                delete_s_button = ttk.Button(item_frame, text="删除", width=6, command=lambda t=title: self.delete_snippet(t), bootstyle="danger-outline")
                delete_s_button.grid(row=0, column=2)

    def populate_profiles_list(self):
        for widget in self.profiles_scrollable_frame.winfo_children(): widget.destroy()
        self.profiles_scrollable_frame.update_idletasks()
        for profile_name in self.profiles.keys():
            item_frame = ttk.Frame(self.profiles_scrollable_frame)
            item_frame.pack(fill="x", pady=3, expand=True)
            item_frame.grid_columnconfigure(0, weight=1)
            profile_button = ttk.Button(item_frame, text=profile_name, bootstyle="primary-outline", command=lambda p=profile_name: self.switch_profile(p))
            profile_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            edit_profile_btn = ttk.Button(item_frame, text="编辑", bootstyle="warning-outline", width=6, command=lambda p=profile_name: self.edit_profile_name(p))
            edit_profile_btn.grid(row=0, column=1, padx=(0,5))
            delete_button = ttk.Button(item_frame, text="删除", bootstyle="danger-outline", width=6, command=lambda p=profile_name: self.delete_specific_profile(p))
            delete_button.grid(row=0, column=2, sticky="e")

    def edit_profile_name(self, old_name):
        self.root.attributes('-topmost', False)
        new_name = simpledialog.askstring("修改方案名称", f"请输入 '{old_name}' 的新名称:", parent=self.root)
        self.root.attributes('-topmost', True)
        if new_name and new_name != old_name:
            if new_name in self.profiles:
                Messagebox.show_warning("该方案名称已存在！", "警告")
                return
            self.profiles[new_name] = self.profiles.pop(old_name)
            self.save_profiles()
            if self.current_profile_name == old_name:
                self.current_profile_name = new_name
            self.populate_profiles_list()
            self.refresh_ui()

    def refresh_ui(self):
        self.profile_name_label.configure(text=self.current_profile_name)
        if self.is_edit_mode:
            self.edit_button.configure(text="完成", bootstyle="success-outline")
            self.navbar.grid_columnconfigure(2, weight=0)
            self.delete_profile_button.grid(row=0, column=2, sticky="e", padx=5)
            self.bottom_bar.grid()
        else:
            self.edit_button.configure(text="编辑", bootstyle="secondary-outline")
            self.delete_profile_button.grid_remove()
            self.bottom_bar.grid_remove()
        self.populate_snippets()

    def show_view(self, view_name):
        if self._current_view: self._current_view.grid_forget()
        if view_name == "profiles":
            self.edit_button.configure(state="disabled")
            self.bottom_bar.grid_remove()
        else:
            self.edit_button.configure(state="normal")
            if self.is_edit_mode:
                self.bottom_bar.grid()
            else:
                self.bottom_bar.grid_remove()
        if view_name == "home": self._current_view = self.home_view
        elif view_name == "edit": self._current_view = self.edit_view
        elif view_name == "profiles": self._current_view = self.profiles_view
        self._current_view.grid(row=0, column=0, sticky="nsew")

    def go_to_profiles_view(self): self.populate_profiles_list(); self.show_view("profiles")
    def go_to_add_view(self): self._editing_snippet_original_title = None; self.edit_view_label.configure(text="新增片段"); self.snippet_title_entry.delete(0, "end"); self.snippet_content_textbox.delete("1.0", "end"); self.show_view("edit")
    def go_to_edit_view(self, title_to_edit): self._editing_snippet_original_title = title_to_edit; content = self.profiles[self.current_profile_name].get(title_to_edit, ""); self.edit_view_label.configure(text="编辑片段"); self.snippet_title_entry.delete(0, "end"); self.snippet_title_entry.insert(0, title_to_edit); self.snippet_content_textbox.delete("1.0", "end"); self.snippet_content_textbox.insert("1.0", content); self.show_view("edit")

    def save_snippet(self):
        new_title = self.snippet_title_entry.get().strip()
        new_content = self.snippet_content_textbox.get("1.0", "end-1c").strip()
        if not new_title:
            Messagebox.show_error("标题不能为空！", "错误"); return
        current_snippets = self.profiles[self.current_profile_name]
        if self._editing_snippet_original_title:
            if new_title != self._editing_snippet_original_title and new_title in current_snippets:
                Messagebox.show_warning("该标题已存在！", "警告"); return
            if self._editing_snippet_original_title in current_snippets:
                del current_snippets[self._editing_snippet_original_title]
        elif new_title in current_snippets:
            Messagebox.show_warning("该标题已存在！", "警告"); return
        current_snippets[new_title] = new_content
        self.save_profiles()
        self.refresh_ui()
        self.show_view("home")

    def switch_profile(self, profile_name): self.current_profile_name = profile_name; self.is_edit_mode = False; self.show_view("home"); self.refresh_ui()

    def add_new_profile(self):
        self.root.attributes('-topmost', False)
        dialog = simpledialog.askstring("新增方案", "请输入新方案的名称:", parent=self.root)
        self.root.attributes('-topmost', True)
        if dialog and dialog not in self.profiles:
            self.profiles[dialog] = {}
            self.save_profiles()
            self.populate_profiles_list()
        elif dialog:
            Messagebox.show_warning("该方案名称已存在！", "警告")

    def delete_current_profile(self):
        self.delete_specific_profile(self.current_profile_name, from_navbar=True)

    def delete_specific_profile(self, profile_name, from_navbar=False):
        if len(self.profiles) <= 1:
            Messagebox.show_error("无法删除最后一个方案！", "错误")
            return
        self.root.attributes('-topmost', False)
        result = Messagebox.show_question("确认删除", title="确认删除", buttons=["取消:secondary", "确认:danger"])
        self.root.attributes('-topmost', True)
        if result == '确认':
            del self.profiles[profile_name]
            self.save_profiles()
            if self.current_profile_name == profile_name:
                self.current_profile_name = next(iter(self.profiles))
                self.is_edit_mode = False
                self.show_view("home")
            if from_navbar:
                self.show_view("home")
            else:
                self.populate_profiles_list()

    def delete_snippet(self, title):
        self.root.attributes('-topmost', False)
        result = Messagebox.show_question("确认删除", title="确认删除", buttons=["取消:secondary", "确认:danger"])
        self.root.attributes('-topmost', True)
        if result == '确认':
            current_snippets = self.profiles[self.current_profile_name]
            if title in current_snippets:
                del current_snippets[title]
                self.save_profiles()
                self.populate_snippets()

    def load_profiles(self):
        git_preset = {
            "克隆仓库 (clone)": "git clone ",
            "查看状态 (status)": "git status",
            "添加所有更改 (add all)": "git add .",
            "提交更改 (commit)": 'git commit -m ""',
            "推送到远程 (push)": "git push",
            "拉取更新 (pull)": "git pull",
            "查看日志 (log)": "git log --oneline",
            "创建新分支 (branch new)": "git checkout -b ",
            "切换分支 (checkout)": "git checkout ",
            "合并分支 (merge)": "git merge "
        }
        default_data = {"默认方案": git_preset}
        if not os.path.exists(DATA_FILE):
            return default_data
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if data else default_data
        except (json.JSONDecodeError, IOError):
            return default_data

    def save_profiles(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.profiles, f, indent=4, ensure_ascii=False)

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()

    def setup_hotkey(self): keyboard.add_hotkey('ctrl+alt+c', self.toggle_window)

    def on_closing(self):
        keyboard.remove_all_hotkeys()
        self.root.destroy()

    def paste_snippet(self, content):
        try:
            pyperclip.copy(content)
            self.hide_window()
            time.sleep(0.2)
            modifier_key = 'command' if sys.platform == 'darwin' else 'ctrl'
            pyautogui.hotkey(modifier_key, 'v')
        except Exception as e:
            Messagebox.show_error(f"操作失败: {e}", "错误")
            self.show_window()

    def toggle_edit_mode(self):
        self.is_edit_mode = not self.is_edit_mode
        self.refresh_ui()

# ★★★ 核心改动：恢复正确的程序主入口 ★★★
if __name__ == "__main__":
    root = ttk.Window(themename="cyborg")
    app = SnippetApp(root)
    
    # 1. 设置托盘图标（这会在后台启动一个线程）
    app.setup_tray_icon()

    # 2. 在主线程中运行Tkinter的事件循环
    root.mainloop()