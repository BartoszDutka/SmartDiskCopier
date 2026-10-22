import os
import shutil
import time
import queue
from datetime import datetime
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.scrolledtext import ScrolledText
from ttkthemes import ThemedTk
import sys
import os.path
from translations import TRANSLATIONS  # Dodaj import tłumaczeń
import json
import tkinter.messagebox as messagebox  # Dodaj ten import na początku pliku

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DiskCopier:
    def __init__(self):
        self.ui_queue = queue.Queue()
        self.ui_queue_lock = threading.Lock()
        self.pending_statuses = {}
        self.ui_thread_id = threading.get_ident()
        self.config_path = self.get_config_path()
        self.config = self.load_config()
        self.root = ThemedTk(theme="azure")
        self.current_language = self.config.get('default_language', 'pl')
        self.root.title(self.get_text('window_title'))
        self.refresh_button = None  # Dodaj tę linię na początku __init__
        self.exit_button = None  # Dodaj tę linię
        self.is_copying = False  # Stan kopiowania
        self.is_exiting = False  # Dodaj flagę zamykania
        
        # Zmniejszone okno do 70% ekranu
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.72)
        window_height = int(screen_height * 0.74)
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(900, 620)
        
        # Konfiguracja zachowania przy zmianie rozmiaru
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Konfiguracja stylów
        self.style = ttk.Style()
        
        # Kolory
        self.colors = {
            'primary': '#1E3A5F',
            'secondary': '#2563EB',
            'accent': '#14B8A6',
            'background': '#F4F7FB',
            'surface': '#FFFFFF',
            'text': '#172033',
            'text_secondary': '#64748B',
            'border': '#DCE4EF',
            'muted_surface': '#EEF3F8'
        }
        
        # Konfiguracja stylów
        self.style.configure('Main.TFrame', background=self.colors['background'])
        self.style.configure('Toolbar.TFrame', background=self.colors['surface'])
        self.style.configure('ToolbarAccent.TFrame', background=self.colors['primary'])
        self.style.configure('Title.TLabel',
                           font=('Segoe UI', 16, 'bold'),
                           background=self.colors['surface'],
                           foreground=self.colors['primary'])
        self.style.configure('Subtitle.TLabel',
                           font=('Segoe UI', 9),
                           background=self.colors['surface'],
                           foreground=self.colors['text_secondary'])
        self.style.configure('Card.TLabelframe',
                           background=self.colors['surface'],
                           borderwidth=0,
                           relief='flat')
        self.style.configure('Card.TLabelframe.Label',
                           background=self.colors['surface'],
                           foreground=self.colors['text'],
                           font=('Segoe UI', 10, 'bold'),
                           padding=5)
        
        # Style dla przycisków
        self.style.configure('Action.TButton',
                           font=('Segoe UI', 9),
                           padding=(10, 6))
        self.style.configure('Primary.TButton',
                           font=('Segoe UI', 9, 'bold'),
                           padding=(12, 7))
        
        # Style dla etykiet
        self.style.configure('DriveTitle.TLabel',
                           font=('Segoe UI', 10, 'bold'),
                           background=self.colors['primary'],
                           foreground='white',
                           padding=(10, 7))
        
        self.style.configure('Header.TLabel',
                           font=('Segoe UI', 10, 'bold'),
                           background=self.colors['surface'],
                           foreground=self.colors['text'],
                           padding=(3, 5))
        
        self.style.configure('Info.TLabel',
                           font=('Segoe UI', 9),
                           background=self.colors['surface'],
                           foreground=self.colors['text_secondary'],
                           padding=(3, 2))

        self.style.configure('CardContent.TFrame',
                           background=self.colors['surface'])
        self.style.configure('Empty.TLabel',
                           font=('Segoe UI', 10),
                           background=self.colors['muted_surface'],
                           foreground=self.colors['text_secondary'],
                           padding=20)
        
        # Styl dla paska postępu
        self.style.configure("Modern.Horizontal.TProgressbar",
                           troughcolor=self.colors['muted_surface'],
                           background=self.colors['accent'],
                           thickness=8)

        self.destination_root = self.config.get('target_path', r'\\qnap4\d-plytki\Plytki')
        self.drives = []
        self.drive_statuses = {}
        self.progress_bars = {}
        self.status_labels = {}
        self.substatus_labels = {}  # Dodanie drugiego statusu
        self.language_buttons = {}  # Dodaj to pole
        self.current_statuses = {}  # Dodaj słownik do przechowywania aktualnych statusów
        self.log_history = []  # Dodaj historię logów
        
        # Dodaj stałe wymiary dla kafelków
        self.DRIVE_CARD_HEIGHT = 150  # Stała wysokość kafelka
        self.DRIVE_CARD_WIDTH = 300   # Stała szerokość kafelka
        self.DRIVE_CARD_PADDING = 10  # Padding wewnętrzny
        
        # Dodaj style dla kafelków
        self.style.configure('DriveCard.TLabelframe',
                           background=self.colors['surface'],
                           borderwidth=0,
                           relief='flat',
                           padding=0)
        
        self.style.configure('StatusFrame.TFrame',
                           background=self.colors['surface'],
                           height=80)  # Stała wysokość dla obszaru statusu

        self.setup_gui()
        self.update_interface_language()  # Dodaj to wywołanie po setup_gui
        self.detect_drives()  # Pierwsze wykrycie napędów
        
        self.start_monitoring()
        self.root.after(100, self.process_ui_queue)

    def get_config_path(self):
        """Zwraca ścieżkę do pliku konfiguracyjnego"""
        # Najpierw sprawdź czy config.json istnieje w katalogu aplikacji
        if getattr(sys, 'frozen', False):
            # Jeśli aplikacja jest skompilowana (exe)
            app_dir = os.path.dirname(sys.executable)
        else:
            # Jeśli uruchamiane jako skrypt Python
            app_dir = os.path.dirname(os.path.abspath(__file__))
            
        return os.path.join(app_dir, 'config.json')

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default config if not exists
            default_config = {
                "target_path": r"\\qnap4\d-plytki\Plytki",
                "default_language": "pl",
                "version": "1.0.0"
            }
            self.save_config(default_config)
            return default_config
        except Exception as e:
            self.log('config_load_error', True, error=str(e))
            return {}

    def save_config(self, config_data=None):
        """Save current configuration to JSON file"""
        if config_data is None:
            config_data = {
                "target_path": self.destination_root,
                "default_language": self.current_language,
                "version": "1.0.0"
            }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log('config_save_error', True, error=str(e))

    def setup_gui(self):
        self.main_container = ttk.Frame(self.root, style='Main.TFrame')
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        controls_frame = ttk.Frame(self.main_container)
        controls_frame.pack(fill='x', pady=(0, 5))

        top_buttons_frame = ttk.Frame(controls_frame, style='ToolbarAccent.TFrame')
        top_buttons_frame.pack(fill='x', pady=(0, 5))

        title_frame = ttk.Frame(top_buttons_frame, style='ToolbarAccent.TFrame')
        title_frame.pack(side='left', fill='x', expand=True, padx=12, pady=8)
        self.style.configure('TitleOnAccent.TLabel',
                           font=('Segoe UI', 16, 'bold'),
                           background=self.colors['primary'],
                           foreground='white')
        self.style.configure('SubtitleOnAccent.TLabel',
                           font=('Segoe UI', 9),
                           background=self.colors['primary'],
                           foreground='#D7E5F5')
        ttk.Label(
            title_frame,
            text=self.get_text('window_title'),
            style='TitleOnAccent.TLabel'
        ).pack(anchor='w')
        self.app_subtitle_label = ttk.Label(
            title_frame,
            text=self.get_text('app_subtitle'),
            style='SubtitleOnAccent.TLabel'
        )
        self.app_subtitle_label.pack(anchor='w', pady=(2, 0))

        self.exit_button = ttk.Button(
            top_buttons_frame,
            text=self.get_text('exit_btn'),
            command=self.confirm_exit,
            style='Action.TButton'
        )
        self.exit_button.pack(side='right', padx=12, pady=12)

        settings_frame = ttk.Frame(controls_frame)
        settings_frame.pack(fill='x', pady=(2, 5))

        lang_buttons_frame = ttk.Frame(settings_frame)
        lang_buttons_frame.pack(side='left', padx=(5, 15))
        
        self.current_lang_label = ttk.Label(
            lang_buttons_frame,
            text=self.get_text('current_lang'),
            style='Info.TLabel'
        )
        self.current_lang_label.pack(side='left', padx=(0, 5))

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

        folder_frame = ttk.LabelFrame(
            controls_frame,
            text="",
            style='Card.TLabelframe',
            padding=(12, 8)
        )
        folder_frame.pack(fill='x', padx=5, pady=(2, 6))

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
        folder_entry = ttk.Entry(
            folder_content,
            textvariable=self.folder_path,
            width=1,
            font=('Segoe UI', 9)
        )
        folder_entry.pack(side='left', padx=10, fill='x', expand=True)
        
        self.choose_button = ttk.Button(
            folder_content,
            text=self.get_text('choose_btn'),
            command=self.choose_folder,
            style='Action.TButton'
        )
        self.choose_button.pack(side='left')

        self.refresh_button = ttk.Button(
            settings_frame,
            text=self.get_text('refresh_drives'),
            command=self.detect_drives,
            style='Primary.TButton'
        )
        self.refresh_button.pack(side='right', padx=5)

        # Ramka na napędy
        self.drives_container = ttk.LabelFrame(
            self.main_container,
            text=self.get_text('drives_frame'),
            style='Card.TLabelframe',
            padding=10
        )
        self.drives_container.pack(fill='both', expand=True, padx=5, pady=(4, 6))
        
        self.drives_frame = ttk.Frame(self.drives_container, style='Main.TFrame')
        self.drives_frame.pack(fill='both', expand=True)

        # Panel logów
        log_frame = ttk.LabelFrame(
            self.main_container,
            text="Log",
            style='Card.TLabelframe',
            padding=10
        )
        log_frame.pack(fill='x', padx=5, pady=(0, 0))
        
        self.log_text = ScrolledText(
            log_frame,
            height=4,
            font=('Consolas', 8),
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
            
            # Save new language to config
            self.save_config()

    def update_interface_language(self):
        """Aktualizuje teksty w interfejsie"""
        # Aktualizacja głównych elementów
        self.root.title(self.get_text('window_title'))
        
        # Aktualizacja przycisku odświeżania
        if self.refresh_button:
            self.refresh_button.config(text=self.get_text('refresh_drives'))
        
        self.drives_container.configure(text=self.get_text('drives_frame'))
        self.app_subtitle_label.config(text=self.get_text('app_subtitle'))
        
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

        # Aktualizacja przycisku wyjścia
        if self.exit_button:
            self.exit_button.config(text=self.get_text('exit_btn'))

    def log(self, message, translate=True, **kwargs):
        """
        Rozszerzona metoda logowania z obsługą tłumaczeń
        translate: czy wiadomość ma być tłumaczona
        kwargs: parametry do formatowania wiadomości
        """
        if threading.get_ident() != self.ui_thread_id:
            self.ui_queue.put(('log', (message, translate, kwargs)))
            return

        self._log_on_ui_thread(message, translate, kwargs)

    def _log_on_ui_thread(self, message, translate, kwargs):
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
            # Save new path to config
            self.save_config()

    def detect_drives(self):
        """Ulepszona implementacja wykrywania napędów CD/DVD"""
        try:
            self.drives = []
            
            # Importy potrzebne do wykrywania napędów
            import win32api
            import win32con
            import win32file
            import win32wnet

            def check_remote_drive(drive_path):
                try:
                    # Pobierz informacje o napędzie sieciowym
                    drive_info = win32wnet.WNetGetConnection(drive_path[0] + ':')
                    # Sprawdź czy to napęd CD/DVD
                    if any(x in drive_info.upper() for x in ['CD', 'DVD', 'OPTICAL']):
                        return True
                except win32wnet.error:
                    return False
                return False

            # Pobierz wszystkie litery dysków w systemie
            drives = win32api.GetLogicalDriveStrings()
            drives = drives.split('\000')[:-1]

            for drive in drives:
                try:
                    drive_type = win32file.GetDriveType(drive)
                    
                    # Sprawdź lokalne napędy CD/DVD
                    if drive_type == win32con.DRIVE_CDROM:
                        if drive not in self.drives:
                            self.drives.append(drive)
                            self.log('detected_drive_system', True, drive=drive)
                    
                    # Sprawdź napędy sieciowe/przekierowane
                    elif drive_type == win32con.DRIVE_REMOTE:
                        try:
                            # Metoda 1: Sprawdź przez WNetGetConnection
                            if check_remote_drive(drive):
                                if drive not in self.drives:
                                    self.drives.append(drive)
                                    self.log('detected_drive_remote', True, drive=drive)
                                continue

                            # Metoda 2: Sprawdź nazwę woluminu
                            volume_name = win32api.GetVolumeInformation(drive)[0]
                            if volume_name and any(x in volume_name.upper() for x in ['CD', 'DVD', 'OPTICAL']):
                                if drive not in self.drives:
                                    self.drives.append(drive)
                                    self.log('detected_drive_remote', True, drive=drive)
                                continue

                            # Metoda 3: Sprawdź mapowanie RDP
                            import winreg
                            rdp_key = winreg.OpenKey(
                                winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Terminal Server Client\Default\AddIns\RDPDR\RDPDR\Devices"
                            )
                            try:
                                i = 0
                                while True:
                                    name, value, _ = winreg.EnumValue(rdp_key, i)
                                    if drive[0].upper() == name[0].upper() and 'CDROM' in value.upper():
                                        if drive not in self.drives:
                                            self.drives.append(drive)
                                            self.log('detected_drive_remote', True, drive=drive)
                                        break
                                    i += 1
                            except WindowsError:
                                pass
                            finally:
                                winreg.CloseKey(rdp_key)

                        except Exception as e:
                            self.log('drive_check_error', True, drive=drive, error=str(e))

                except Exception as e:
                    self.log('drive_check_error', True, drive=drive, error=str(e))

            # Sortowanie i usuwanie duplikatów
            self.drives = sorted(list(set(self.drives)))
            
            # Wyczyść starą zawartość drives_frame
            for widget in self.drives_frame.winfo_children():
                widget.destroy()
            
            # Ustawienie gridu dla kafelków
            drive_container = ttk.Frame(self.drives_frame, style='Main.TFrame')
            drive_container.pack(fill='both', expand=True, padx=6, pady=4)
            
            # Konfiguracja kolumn z równymi wagami
            drive_container.grid_columnconfigure(0, weight=1, uniform='drive_col')
            drive_container.grid_columnconfigure(1, weight=1, uniform='drive_col')

            # Tworzenie kafelków dla napędów
            for idx, drive in enumerate(self.drives):
                row = idx // 2
                col = idx % 2
                
                # Kontener na kafelek z ustaloną wysokością i szerokością
                drive_card = tk.Frame(
                    drive_container,
                    background=self.colors['surface'],
                    highlightbackground=self.colors['border'],
                    highlightcolor=self.colors['border'],
                    highlightthickness=1,
                    bd=0
                )
                drive_card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
                drive_card.grid_propagate(False)
                
                # Wymuszenie minimalnych wymiarów
                drive_card.configure(height=self.DRIVE_CARD_HEIGHT, width=self.DRIVE_CARD_WIDTH)
                
                # Kontener na zawartość
                drive_content = ttk.Frame(drive_card, style='CardContent.TFrame')
                drive_content.pack(fill='both', expand=True, padx=1, pady=1)
                
                # Tytuł napędu z ikoną
                ttk.Label(
                    drive_content,
                    text=self.get_text('drive_label').format(drive=drive),
                    style='DriveTitle.TLabel'
                ).pack(fill='x', pady=(0, 5))
                
                # Status container z ustaloną wysokością
                status_container = ttk.Frame(drive_content)
                status_container.pack(fill='both', expand=True, pady=(0, 5))
                
                # Główny status z większym wraplength
                self.status_labels[drive] = ttk.Label(
                    status_container,
                    text=f"{self.get_text('status_prefix')}{self.get_text('waiting')}",
                    style='Header.TLabel',
                    wraplength=self.DRIVE_CARD_WIDTH - 30
                )
                self.status_labels[drive].pack(fill='x', pady=(0, 2))
                
                # Dodatkowy status z większym wraplength
                self.substatus_labels[drive] = ttk.Label(
                    status_container,
                    text=self.get_text('insert_disc'),
                    style='Info.TLabel',
                    wraplength=self.DRIVE_CARD_WIDTH - 30
                )
                self.substatus_labels[drive].pack(fill='x')
                
                # Progress bar zawsze na dole
                self.progress_bars[drive] = ttk.Progressbar(
                    drive_content,
                    style="Modern.Horizontal.TProgressbar",
                    mode='determinate'
                )
                self.progress_bars[drive].pack(fill='x', side='bottom')
            
            self.log('total_drives_detected', True, count=len(self.drives))
            if not self.drives:
                ttk.Label(
                    self.drives_frame,
                    text=self.get_text('no_drives'),
                    style='Empty.TLabel'
                ).pack(fill='x', padx=20, pady=20)
                self.log('no_drives', True)
                
        except Exception as e:
            self.log('drive_detect_error', True, error=str(e))
            ttk.Label(self.drives_frame, text=self.get_text('drive_detect_error')).pack()

    def update_status(self, drive, main_status, sub_status="", progress=None):
        """Aktualizacja obu statusów i paska postępu z tłumaczeniami"""
        if threading.get_ident() != self.ui_thread_id:
            with self.ui_queue_lock:
                was_pending = drive in self.pending_statuses
                self.pending_statuses[drive] = (drive, main_status, sub_status, progress)
            if not was_pending:
                self.ui_queue.put(('status', drive))
            return
        self._update_status_on_ui_thread(drive, main_status, sub_status, progress)

    def _update_status_on_ui_thread(self, drive, main_status, sub_status="", progress=None):
        if drive in self.status_labels:
            # Zapisz aktualny status
            self.current_statuses[drive] = {
                'main': main_status,
                'sub': sub_status,
                'progress': progress
            }

            # Obsługa specjalnego przypadku dla statusu kopiowania z procentem
            if "Kopiowanie (" in main_status or "Copying (" in main_status:
                # Wyciągnij tylko liczbę z nawiasów, bez znaku %
                progress_value = main_status.split('(')[1].split('%')[0].strip()
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
        
        # Sprawdź czy rozpoczęło się kopiowanie
        if "copying" in main_status.lower() and not self.is_copying:
            self.is_copying = True
        
        # Sprawdź czy zakończono kopiowanie
        if "disc_ejected" in main_status.lower() and self.is_copying:
            self.is_copying = False

    def process_ui_queue(self):
        """Wykonuje ograniczoną liczbę aktualizacji UI z wątku głównego."""
        for _ in range(100):
            try:
                operation, args = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            if operation == 'status':
                with self.ui_queue_lock:
                    status_args = self.pending_statuses.pop(args, None)
                if status_args:
                    self._update_status_on_ui_thread(*status_args)
            elif operation == 'log':
                self._log_on_ui_thread(*args)
        if not self.is_exiting:
            self.root.after(100, self.process_ui_queue)

    def copy_disc_content(self, drive):
        try:
            while True:
                self.update_status(drive, "waiting", "insert_disc", 0)
                if os.path.exists(drive) and os.listdir(drive):
                    self.update_status(drive, "initialization", "preparing", 0)
                    
                    # Get Windows username
                    username = os.getenv('USERNAME')
                    folder_name = datetime.now().strftime(f"Plyta_{drive[0]}_{username}_%Y%m%d_%H%M%S")
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
                            # Usuwamy znak % z tekstu statusu
                            self.update_status(drive, 
                                            f"Kopiowanie ({progress})", 
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

    def confirm_exit(self):
        """Pokazuje okno potwierdzenia przed wyjściem z programu"""
        # Oblicz pozycję okna dialogowego względem głównego okna
        window_x = self.root.winfo_x()
        window_y = self.root.winfo_y()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Stwórz własne okno dialogowe
        dialog = tk.Toplevel(self.root)
        dialog.title(self.get_text('exit_confirm_title'))
        
        # Ustaw rozmiar okna
        dialog_width = 300
        dialog_height = 150
        
        # Wycentruj okno dialogowe względem głównego okna
        dialog_x = window_x + (window_width - dialog_width) // 2
        dialog_y = window_y + (window_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")
        
        # Zablokuj zmianę rozmiaru
        dialog.resizable(False, False)
        
        # Ustaw modalność
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Dodaj pytanie
        question_label = ttk.Label(
            dialog,
            text=self.get_text('exit_confirm'),
            style='Header.TLabel',
            wraplength=250  # Zawijanie tekstu
        )
        question_label.pack(pady=(20, 30))
        
        # Kontener na przyciski
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill='x', padx=20)
        
        # Przyciski
        ttk.Button(
            button_frame,
            text="Tak",
            command=lambda: self.exit_application(dialog),
            style='Action.TButton',
            width=10
        ).pack(side='left', padx=10)
        
        ttk.Button(
            button_frame,
            text="Nie",
            command=dialog.destroy,
            style='Action.TButton',
            width=10
        ).pack(side='right', padx=10)
        
        # Wycentruj kontener z przyciskami
        button_frame.pack_configure(anchor='center')
        
        # Czekaj na zamknięcie okna
        dialog.wait_window()

    def exit_application(self, dialog=None):
        """Bezpieczne zamykanie aplikacji"""
        self.is_exiting = True
        if dialog:
            dialog.destroy()
        
        # Zapisz konfigurację przed wyjściem
        self.save_config()
        
        # Zniszcz główne okno i zakończ aplikację
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        """Uruchamia aplikację"""
        # Dodaj obsługę zamykania okna
        self.root.protocol('WM_DELETE_WINDOW', self.confirm_exit)
        
        try:
            self.root.mainloop()
        finally:
            # Upewnij się, że program zostanie prawidłowo zamknięty
            if not self.is_exiting:
                self.exit_application()

if __name__ == "__main__":
    CHECK_DELAY = 15
    mutex = ctypes.windll.kernel32.CreateMutexW(
        None, False, "Global\\SmartDiskCopierSingleInstance"
    )
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(
            None,
            "Aplikacja SmartDiskCopier jest już uruchomiona.",
            "SmartDiskCopier",
            0x00000010
        )
        ctypes.windll.kernel32.CloseHandle(mutex)
        sys.exit(0)

    try:
        app = DiskCopier()
        app.run()
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)
