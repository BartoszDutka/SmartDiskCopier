import os
import shutil
import time
from datetime import datetime
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.scrolledtext import ScrolledText
from ttkthemes import ThemedTk
import wmi  # Dodaj ten import
import string  # dodaj ten import
import sys
import os.path
from translations import TRANSLATIONS  # Dodaj import tłumaczeń

class DiskCopier:
    def __init__(self):
        self.root = ThemedTk(theme="azure")
        self.current_language = 'pl'
        self.root.title(self.get_text('window_title'))
        
        # Zmniejszone okno do 70% ekranu
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.7)
        window_height = int(screen_height * 0.7)
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Konfiguracja zachowania przy zmianie rozmiaru
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Konfiguracja stylów
        self.style = ttk.Style()
        
        # Kolory
        self.colors = {
            'primary': '#1976D2',      # Ciemniejszy niebieski
            'secondary': '#2196F3',    # Niebieski
            'accent': '#64B5F6',       # Jasny niebieski
            'background': '#E3F2FD',   # Bardzo jasny niebieski
            'surface': '#FFFFFF',      # Biały
            'text': '#212121',         # Ciemnoszary
            'text_secondary': '#757575' # Średnioszary
        }
        
        # Konfiguracja stylów
        self.style.configure('Main.TFrame', background=self.colors['background'])
        self.style.configure('Card.TLabelframe',
                           background=self.colors['surface'],
                           borderwidth=0,
                           relief='flat')
        self.style.configure('Card.TLabelframe.Label',
                           background=self.colors['primary'],
                           foreground='white',
                           font=('Segoe UI', 10, 'bold'),
                           padding=5)
        
        # Style dla przycisków
        self.style.configure('Action.TButton',
                           font=('Segoe UI', 9),
                           padding=5)
        
        # Style dla etykiet
        self.style.configure('DriveTitle.TLabel',
                           font=('Segoe UI', 10, 'bold'),
                           background=self.colors['primary'],
                           foreground='white',
                           padding=5)
        
        self.style.configure('Header.TLabel',
                           font=('Segoe UI', 10, 'bold'),
                           background=self.colors['surface'],
                           foreground=self.colors['primary'],
                           padding=3)
        
        self.style.configure('Info.TLabel',
                           font=('Segoe UI', 9),
                           background=self.colors['surface'],
                           foreground=self.colors['text_secondary'],
                           padding=2)
        
        # Styl dla paska postępu
        self.style.configure("Modern.Horizontal.TProgressbar",
                           troughcolor=self.colors['background'],
                           background=self.colors['secondary'],
                           thickness=10)

        self.destination_root = os.path.join(os.path.expanduser('~'), 'Desktop', 'DiscCopies')
        self.drives = []
        self.drive_statuses = {}
        self.progress_bars = {}
        self.status_labels = {}
        self.substatus_labels = {}  # Dodanie drugiego statusu
        self.language_buttons = {}  # Dodaj to pole
        self.current_statuses = {}  # Dodaj słownik do przechowywania aktualnych statusów
        self.log_history = []  # Dodaj historię logów
        
        self.setup_gui()
        self.update_interface_language()  # Dodaj to wywołanie po setup_gui
        self.detect_drives()  # Pierwsze wykrycie napędów
        
        self.start_monitoring()

    def setup_gui(self):
        # Konfiguracja głównego kontenera
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)
        
        # Canvas i scrollbar
        canvas = tk.Canvas(main_frame, background=self.colors['background'])
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        # Główny kontener na zawartość
        self.main_container = ttk.Frame(canvas, style='Main.TFrame')
        
        # Konfiguracja scrollowania
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pakowanie elementów scrollowania
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # Tworzenie okna dla głównego kontenera
        canvas_window = canvas.create_window(
            (0, 0),
            window=self.main_container,
            anchor='nw',
            tags='self.main_container'
        )
        
        # Funkcje konfiguracji scrollowania
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        def configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        # Bindowanie zdarzeń
        self.main_container.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', configure_canvas)
        
        # Umożliwienie scrollowania myszką
        def on_mousewheel(event):
            canvas.yview_scroll(-1 * int((event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Kontenery na elementy interfejsu
        controls_frame = ttk.Frame(self.main_container)
        controls_frame.pack(fill='x', pady=(0, 5))
        
        # Panel językowy
        lang_frame = ttk.LabelFrame(
            controls_frame,
            text="",
            style='Card.TLabelframe',
            padding=5
        )
        lang_frame.pack(fill='x', padx=3, pady=2)
        
        # Kontener na przyciski języków
        lang_buttons_frame = ttk.Frame(lang_frame)
        lang_buttons_frame.pack(fill='x')
        
        self.current_lang_label = ttk.Label(
            lang_buttons_frame,
            text=self.get_text('current_lang'),
            style='Header.TLabel'
        )
        self.current_lang_label.pack(side='left', padx=5)

        # Przyciski języków
        for lang in ['pl', 'en']:
            btn = ttk.Button(
                lang_buttons_frame,
                text=self.get_text(f'lang_{lang}'),
                command=lambda l=lang: self.change_language(l),
                style='Action.TButton'
            )
            btn.pack(side='left', padx=2)
            self.language_buttons[lang] = btn

        # Panel wyboru folderu
        folder_frame = ttk.LabelFrame(
            controls_frame,
            text="",
            style='Card.TLabelframe',
            padding=10
        )
        folder_frame.pack(fill='x', padx=5, pady=5)

        # Kontener na elementy folderu
        folder_content = ttk.Frame(folder_frame)
        folder_content.pack(fill='x')
        
        self.folder_label = ttk.Label(
            folder_content,
            text=self.get_text('target_folder'),
            style='Header.TLabel'
        )
        self.folder_label.pack(side='left')
        
        self.folder_path = tk.StringVar(value=self.destination_root)
        ttk.Entry(
            folder_content,
            textvariable=self.folder_path,
            width=50,
            font=('Segoe UI', 9)
        ).pack(side='left', padx=10)
        
        self.choose_button = ttk.Button(
            folder_content,
            text=self.get_text('choose_btn'),
            command=self.choose_folder,
            style='Action.TButton'
        )
        self.choose_button.pack(side='left')

        # Przycisk odświeżania
        refresh_button = ttk.Button(
            controls_frame,
            text=self.get_text('refresh_drives'),
            command=self.detect_drives,
            style='Action.TButton'
        )
        refresh_button.pack(pady=(0, 10))

        # Ramka na napędy
        drives_container = ttk.LabelFrame(
            self.main_container,
            text=self.get_text('drives_frame'),
            style='Card.TLabelframe',
            padding=15
        )
        drives_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create inner frame for drives
        self.drives_frame = ttk.Frame(drives_container, style='Main.TFrame')
        self.drives_frame.pack(fill='both', expand=True)

        # Panel logów
        log_frame = ttk.LabelFrame(
            self.main_container,
            text="Log",
            style='Card.TLabelframe',
            padding=15
        )
        log_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        self.log_text = ScrolledText(
            log_frame,
            height=5,  # Zmniejszona wysokość
            font=('Consolas', 8),  # Mniejsza czcionka
            background=self.colors['surface'],
            foreground=self.colors['text'],
            relief='flat',
            padx=5,
            pady=5
        )
        self.log_text.pack(fill='both', expand=True)

    def get_text(self, key):
        """Pobiera tłumaczenie dla danego klucza"""
        return TRANSLATIONS[self.current_language].get(key, key)

    def change_language(self, new_lang):
        """Zmienia język na wybrany"""
        if new_lang != self.current_language:
            self.current_language = new_lang
            self.update_interface_language()
            
            # Aktualizuj label aktualnego języka
            self.current_lang_label.config(text=self.get_text('current_lang'))
            
            # Aktualizuj tekst na przyciskach języków
            for lang, btn in self.language_buttons.items():
                btn.config(text=self.get_text(f'lang_{lang}'))

    def update_interface_language(self):
        """Aktualizuje teksty w interfejsie"""
        # Aktualizacja głównych elementów
        self.root.title(self.get_text('window_title'))
        
        # Find drives container and update its text
        for widget in self.main_container.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and widget.winfo_children() and \
               isinstance(widget.winfo_children()[0], ttk.Frame):
                widget.configure(text=self.get_text('drives_frame'))
                break
        
        # Aktualizacja etykiet i przycisków folderu
        self.folder_label.config(text=self.get_text('target_folder'))
        self.choose_button.config(text=self.get_text('choose_btn'))
        
        # Aktualizacja przycisku odświeżania
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button) and widget.cget('text') in ["Odśwież napędy", "Refresh Drives"]:
                widget.config(text=self.get_text('refresh_drives'))
        
        # Aktualizacja przycisków i etykiet w ramkach
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame) or isinstance(widget, ttk.LabelFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        if child.cget('text') == "Wybierz":
                            child.config(text=self.get_text('choose_btn'))
                    elif isinstance(child, ttk.Label):
                        if "Folder docelowy" in child.cget('text'):
                            child.config(text=self.get_text('target_folder'))
        
        # Aktualizacja etykiet języka
        self.current_lang_label.config(text=self.get_text('current_lang'))
        for lang, btn in self.language_buttons.items():
            btn.config(text=self.get_text(f'lang_{lang}'))
        
        # Odśwież statusy wszystkich napędów
        for drive in self.drives:
            if drive in self.current_statuses:
                status_info = self.current_statuses[drive]
                self.update_status(drive, status_info['main'], status_info['sub'], status_info['progress'])

        # Aktualizacja logów
        self.log_text.delete('1.0', tk.END)
        for log_entry in self.log_history:
            if log_entry['translate']:
                translated_message = self.get_text(log_entry['message']).format(**log_entry['kwargs'])
            else:
                translated_message = log_entry['message'].format(**log_entry['kwargs'])
            self.log_text.insert('end', f"{log_entry['timestamp']}: {translated_message}\n")
        self.log_text.see('end')
        
        # Odśwież napędy aby zaktualizować ich etykiety
        self.detect_drives()

    def log(self, message, translate=True, **kwargs):
        """
        Rozszerzona metoda logowania z obsługą tłumaczeń
        translate: czy wiadomość ma być tłumaczona
        kwargs: parametry do formatowania wiadomości
        """
        if translate:
            translated_message = self.get_text(message).format(**kwargs) if kwargs else self.get_text(message)
        else:
            translated_message = message.format(**kwargs) if kwargs else message

        timestamp = datetime.now().strftime('%H:%M:%S')
        full_message = f"{timestamp}: {translated_message}"
        
        # Zapisz oryginalną wiadomość i parametry do historii
        self.log_history.append({
            'timestamp': timestamp,
            'message': message,
            'translate': translate,
            'kwargs': kwargs
        })
        
        self.log_text.insert('end', full_message + '\n')
        self.log_text.see('end')

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.destination_root)
        if folder:
            self.destination_root = folder
            self.folder_path.set(folder)

    def detect_drives(self):
        """Ulepszona implementacja wykrywania napędów CD/DVD"""
        try:
            self.drives = []
            
            # Metoda 1: Używając WMI
            c = wmi.WMI()
            for cdrom in c.Win32_CDROMDrive():
                if (cdrom.Drive):
                    drive_path = cdrom.Drive + "\\"
                    if drive_path not in self.drives:
                        self.drives.append(drive_path)
                        self.log('detected_drive_wmi', True, drive=cdrom.Drive, caption=cdrom.Caption)
            
            # Metoda 2: Sprawdzanie wszystkich możliwych liter dysków
            for letter in string.ascii_uppercase:
                drive_path = f"{letter}:\\"
                try:
                    drive_type = win32api.GetDriveType(drive_path)
                    if drive_type == win32con.DRIVE_CDROM:
                        if drive_path not in self.drives:
                            self.drives.append(drive_path)
                            self.log('detected_drive_system', True, drive=drive_path)
                except:
                    continue
            
            # Sortowanie i usuwanie duplikatów
            self.drives = sorted(list(set(self.drives)))
            
            # Wyczyść starą zawartość drives_frame
            for widget in self.drives_frame.winfo_children():
                widget.destroy()
            
            # Ustawienie gridu dla kafelków
            drive_container = ttk.Frame(self.drives_frame)
            drive_container.pack(fill='both', expand=True)
            
            drive_container.columnconfigure(0, weight=1)
            drive_container.columnconfigure(1, weight=1)
            
            # Tworzenie kafelków dla napędów
            for idx, drive in enumerate(self.drives):
                row = idx // 2
                col = idx % 2
                
                drive_card = ttk.LabelFrame(
                    drive_container,
                    text="",
                    style='Card.TLabelframe',
                    padding=5  # Zmniejszony padding
                )
                drive_card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
                
                # Create inner frame for drive content
                drive_content = ttk.Frame(drive_card)
                drive_content.pack(fill='both', expand=True)
                
                # Add drive components to drive_content using pack
                ttk.Label(
                    drive_content,
                    text=self.get_text('drive_label').format(drive=drive),
                    style='DriveTitle.TLabel'
                ).pack(fill='x', pady=(0, 10))
                
                # Status container
                status_frame = ttk.Frame(drive_content)
                status_frame.pack(fill='x', expand=True)
                
                # Status labels
                self.status_labels[drive] = ttk.Label(
                    status_frame,
                    text=f"{self.get_text('status_prefix')}{self.get_text('waiting')}",
                    style='Header.TLabel'
                )
                self.status_labels[drive].pack(fill='x')
                
                self.substatus_labels[drive] = ttk.Label(
                    status_frame,
                    text=self.get_text('insert_disc'),
                    style='Info.TLabel'
                )
                self.substatus_labels[drive].pack(fill='x')
                
                # Progress bar
                self.progress_bars[drive] = ttk.Progressbar(
                    drive_content,
                    style="Modern.Horizontal.TProgressbar",
                    mode='determinate'
                )
                self.progress_bars[drive].pack(fill='x', pady=(10, 0))
            
            self.log('total_drives_detected', True, count=len(self.drives))
            if not self.drives:
                ttk.Label(self.drives_frame, text=self.get_text('no_drives')).pack()
                self.log('no_drives', True)
                
        except Exception as e:
            self.log('drive_detect_error', True, error=str(e))
            ttk.Label(self.drives_frame, text=self.get_text('drive_detect_error')).pack()

    def update_status(self, drive, main_status, sub_status="", progress=None):
        """Aktualizacja obu statusów i paska postępu z tłumaczeniami"""
        if drive in self.status_labels:
            # Zapisz aktualny status
            self.current_statuses[drive] = {
                'main': main_status,
                'sub': sub_status,
                'progress': progress
            }

            # Obsługa specjalnego przypadku dla statusu kopiowania z procentem
            if "Kopiowanie (" in main_status or "Copying (" in main_status:
                progress_value = main_status.split('(')[1].split(')')[0]
                translated_status = self.get_text('copying_progress').format(progress=progress_value)
            else:
                translated_status = self.get_text(main_status.lower())

            # Obsługa specjalnego przypadku dla statusu kopiowania pliku
            if "Kopiowanie: " in sub_status or "Copying: " in sub_status:
                filename = sub_status.split(': ')[1]
                translated_substatus = self.get_text('copying_file').format(filename=filename)
            else:
                translated_substatus = self.get_text(sub_status.lower())

            self.status_labels[drive].config(
                text=f"{self.get_text('status_prefix')}{translated_status}")
            self.substatus_labels[drive].config(text=translated_substatus)
            if progress is not None:
                self.progress_bars[drive]['value'] = progress
            self.root.update_idletasks()

    def copy_disc_content(self, drive):
        try:
            while True:
                self.update_status(drive, "waiting", "insert_disc", 0)
                if os.path.exists(drive) and os.listdir(drive):
                    self.update_status(drive, "initialization", "preparing", 0)
                    folder_name = datetime.now().strftime(f"Plyta_{drive[0]}_%Y%m%d_%H%M%S")
                    destination_folder = os.path.join(self.destination_root, folder_name)
                    
                    if not os.path.exists(destination_folder):
                        os.makedirs(destination_folder, exist_ok=True)

                    # Liczenie całkowitego rozmiaru
                    self.update_status(drive, "analysis", "calculating", 0)
                    total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, _, filenames in os.walk(drive)
                        for filename in filenames)
                    
                    copied_size = 0
                    for dirpath, _, filenames in os.walk(drive):
                        for filename in filenames:
                            source_path = os.path.join(dirpath, filename)
                            relative_path = os.path.relpath(dirpath, drive)
                            dest_dir = os.path.join(destination_folder, relative_path)
                            os.makedirs(dest_dir, exist_ok=True)
                            dest_path = os.path.join(dest_dir, filename)
                            
                            shutil.copy2(source_path, dest_path)
                            copied_size += os.path.getsize(source_path)
                            progress = int((copied_size / total_size) * 100)
                            self.update_status(drive, 
                                            f"Kopiowanie ({progress}%)", 
                                            f"Kopiowanie: {filename}", 
                                            progress)
                    
                    self.update_status(drive, "finishing", "ejecting", 100)
                    self.log('copied_content', drive=drive, folder=destination_folder)
                    self.eject_drive(drive)
                    
                    # Reset statusu po wysunięciu
                    time.sleep(2)
                    self.update_status(drive, "disc_ejected", "insert_new", 0)
                    
                time.sleep(CHECK_DELAY)
        except Exception as e:
            self.log('drive_error', drive=drive, error=str(e))
            self.update_status(drive, "drive_detect_error", str(e), 0)

    def eject_drive(self, drive):
        try:
            ctypes.windll.winmm.mciSendStringW(f"open {drive} type CDAudio alias drive", None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f"set drive door open", None, 0, None)
            self.log('drive_ejected', drive=drive)
        except Exception as e:
            self.log('drive_eject_error', drive=drive, error=str(e))

    def start_monitoring(self):
        for drive in self.drives:
            thread = threading.Thread(target=self.copy_disc_content, args=(drive,), daemon=True)
            thread.start()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    CHECK_DELAY = 15
    app = DiskCopier()
    app.run()
