import cv2
import numpy as np
import time
import os
import pygame
import threading
from pynput import keyboard
import tkinter as tk
from tkinter import Label, Frame, messagebox
import mss
import random

pygame.mixer.init()

spell_layout = "Glint"
weapon_layout = "Schwert/Schwert"
sound_enabled = True  # Variable zum Verfolgen des Soundstatus

# Schwellenwert für die Bildsuche
threshold = 0.8  # Standardwert, anpassbar nach Bedarf

# Zu überwachende Bilder
target_images = [
    "conditions/Bleed.png",
    "conditions/Burning.png",
    "conditions/Poison.png",
    "conditions/Torment.png",
    "conditions/Confusion.png"
]
target_images_data = []

# Ordner für die skalierten Bilder
scaled_conditions_dir = "scaled_conditions"
os.makedirs(scaled_conditions_dir, exist_ok=True)

# Bilder laden, in Graustufen umwandeln und skalieren
for img_path in target_images:
    img = cv2.imread(img_path)
    if img is not None:
        # In Graustufen umwandeln
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Skalieren auf 30x26
        scaled_img = cv2.resize(gray_img, (30, 26))

        # Speicher die skalierte Bild im neuen Ordner
        scaled_img_path = os.path.join(scaled_conditions_dir, os.path.basename(img_path))
        cv2.imwrite(scaled_img_path, scaled_img)

        # Füge das skalierte Bild zu den Zielbildern hinzu
        target_images_data.append(scaled_img)
    else:
        print(f"Bild nicht gefunden: {img_path}")

# Pfad zum Sounds-Ordner
sounds_folder = "Sounds"

# Sprüche und deren Eigenschaften
spells = {
    "Glint": {
        "name": "Glint",
        "keys": {
            "6": {"name": "Licht Spenden", "cooldown": 30, "cast_time": 0, "sound": os.path.join(sounds_folder, "GlintHeal.wav"), "status": "ready"},
            "7": {"name": "Blick der Dunkelheit", "cooldown": 20, "cast_time": 0, "sound": os.path.join(sounds_folder, "GazeOfDarkness.wav"), "status": "ready"}
        }
    },
    "Shiro": {
        "name": "Shiro",
        "keys": {
            "6": {"name": "Verzauberte Dolche", "cooldown": 30, "cast_time": 0.5, "sound": os.path.join(sounds_folder, "Enchanted Daggers.wav"), "status": "ready"}
        }
    },
    "Schwert/Schwert": {
        "name": "Schwert/Schwert",
        "keys": {
            "3": {"name": "Unablässiger Angriff", "cooldown": 15, "cast_time": 0.75, "sound": os.path.join(sounds_folder, "Unrelenting Assault.wav"), "status": "ready"}
        }
    },
    "Stab": {
        "name": "Stab",
        "keys": {
            "3": {"name": "Abwehrender Riss", "cooldown": 20, "cast_time": 1.5, "sound": os.path.join(sounds_folder, "Warding Rift.wav"), "status": "ready"},
            "4": {"name": "Erneuernde Welle", "cooldown": 15, "cast_time": 1.0, "sound": os.path.join(sounds_folder, "Renewing Wave.wav"), "status": "ready"},
            "r": {"name": "Schub der Nebel", "cooldown": 25, "cast_time": 1.5, "sound": os.path.join(sounds_folder, "SurgeOfTheMists.wav"), "status": "ready"}
        }
    }
}

spell_cooldowns = {layout: {key: 0 for key in spells[layout]["keys"]} for layout in spells.keys()}


class Overlay:
    def __init__(self, tk_root, title):
        self.root = tk_root
        self.root.title(title)  # Setze den Titel des Fensters
        self.root.overrideredirect(True)
        self.root.wm_attributes('-topmost', True)
        self.root.wm_attributes('-alpha', 0.8)
        self.root.geometry('300x400+50+50')

        self.frame = Frame(self.root, bg='black')
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.label = Label(self.frame, text="", bg='black', fg='white', font=('Arial', 15), justify=tk.LEFT)
        self.label.pack(pady=20)

        # Variablen für die Position
        self.offset_x = 0
        self.offset_y = 0

        # Binden der Maus-Events zum Verschieben des Fensters
        self.frame.bind("<Button-1>", self.click_window)
        self.frame.bind("<B1-Motion>", self.drag_window)

    def click_window(self, event):
        """Speichert die Position der Maus, wenn der Benutzer auf das Fenster klickt."""
        self.offset_x = event.x
        self.offset_y = event.y

    def drag_window(self, event):
        """Verschiebt das Fenster, wenn der Benutzer die Maus zieht."""
        x = event.x_root - self.offset_x
        y = event.y_root - self.offset_y
        self.root.geometry(f"+{x}+{y}")

    def update_text(self, text):
        self.label.config(text=text)

    def set_color(self, color):
        """Setzt die Schriftfarbe des Labels."""
        self.label.config(fg=color)


def play_sound(sound_file):
    if sound_file and sound_enabled:
        pygame.mixer.Sound(sound_file).play()


def monitor_screen():
    # Definieren Sie den Bereich, den Sie überwachen möchten
    x, y = 1339, 1277  # Oben links
    width, height = 296, 74  # Breite und Höhe

    while True:
        # Erfassen Sie den Bildschirmbereich mit mss
        monitor = {
            "top": y,
            "left": x,
            "width": width,
            "height": height,
        }

        with mss.mss() as sct:
            screen = sct.grab(monitor)
            screen_np = np.array(screen)

            # In Graustufen umwandeln
            gray_frame = cv2.cvtColor(screen_np, cv2.COLOR_BGRA2GRAY)

            # Vergleich mit den Zielbildern
            for target_img in target_images_data:
                result = cv2.matchTemplate(gray_frame, target_img, cv2.TM_CCOEFF_NORMED)
                loc = np.where(result >= threshold)

                if len(loc[0]) > 0:  # Wenn Übereinstimmungen gefunden wurden
                    print("Zielbild erkannt! Sound abspielen...")
                    play_sound(os.path.join(sounds_folder, "cleanse.wav"))  # Sound sofort abspielen
                    break  # Verlassen Sie die Schleife, um mehrfaches Auslösen zu vermeiden

        time.sleep(0.1)  # Kurze Pause, um CPU-Ressourcen zu schonen


def check_cooldowns():
    while True:
        time.sleep(1)
        for layout in spell_cooldowns.keys():
            for spell in spell_cooldowns[layout]:
                if spell_cooldowns[layout][spell] > 0:
                    spell_cooldowns[layout][spell] -= 1


def overlay_loop():
    while True:
        overlay_text = f"Layout: {spell_layout}\nWaffen: {weapon_layout}\n\n"

        cooldown_list = []
        for layout in spell_cooldowns:
            for spell, cooldown_time in spell_cooldowns[layout].items():
                spell_name = spells[layout]['keys'][spell]['name']
                if cooldown_time > 0:
                    cooldown_list.append((spell_name, cooldown_time))

        cooldown_list.sort(key=lambda x: x[1], reverse=True)
        for spell_name, cooldown_time in cooldown_list:
            overlay_text += f"{spell_name:<25}: {cooldown_time:>5.1f} s\n"

        overlay.update_text(overlay_text)

        # Überprüfen, ob eine Abklingzeit 5 Sekunden oder weniger beträgt
        for _, cooldown_time in cooldown_list:
            if cooldown_time <= 5:
                overlay.set_color('red')  # Schriftfarbe auf Rot ändern
                break
        else:
            overlay.set_color('white')  # Schriftfarbe auf Weiß zurücksetzen

        time.sleep(0.1)


def switch_spell_layout():
    global spell_layout
    spell_layout = "Shiro" if spell_layout == "Glint" else "Glint"


def switch_weapon_layout():
    global weapon_layout
    weapon_layout = "Stab" if weapon_layout == "Schwert/Schwert" else "Schwert/Schwert"


def on_press(key):
    try:
        if key == keyboard.Key.f1:
            switch_spell_layout()
        elif key == keyboard.Key.shift:
            switch_weapon_layout()
        elif key == keyboard.Key.f10:  # F10 zum Aktivieren/Deaktivieren des Sounds
            toggle_sound()
        elif hasattr(key, 'char') and key.char in {'6', '7', '3', '4', 'r'}:
            handle_key_press(key.char)
    except AttributeError:
        pass


def handle_key_press(char):
    if spell_layout in spells and char in spells[spell_layout]["keys"]:
        activate_spell(spell_layout, char)
    if weapon_layout in spells and char in spells[weapon_layout]["keys"]:
        activate_spell(weapon_layout, char)


def activate_spell(current_layout, char):
    spell_info = spells[current_layout]["keys"][char]
    cooldown = spell_info["cooldown"]
    status = spell_info["status"]

    if spell_cooldowns[current_layout][char] > 0:
        return

    if current_layout == "Glint":
        if status == "ready":
            spell_info["status"] = "activated"
        elif status == "activated":
            spell_info["status"] = "ready"
            spell_cooldowns[current_layout][char] = cooldown
            threading.Thread(target=play_sound_after_cooldown, args=(spell_info["sound"], cooldown)).start()
    else:
        spell_cooldowns[current_layout][char] = cooldown
        threading.Thread(target=play_sound_after_cooldown, args=(spell_info["sound"], cooldown)).start()


def play_sound_after_cooldown(sound_file, cooldown):
    time.sleep(cooldown)
    play_sound(sound_file)


def toggle_sound():
    global sound_enabled
    sound_enabled = not sound_enabled  # Toggle sound status
    print("Sound aktiviert." if sound_enabled else "Sound deaktiviert.")


def show_instructions():
    instructions = (
        "Start des Overlay\n"
        "Beim Start von dem Overlay muss man auf der Legende Glint sein und auf dem Waffenset Schwert/Schwert\n"
        "Andernfalls kann das Overlay die Tasteneingaben nicht richtig verarbeiten.\n\n"
        "Steuerung des Overlays:\n"
        "F1: Wechsel zwischen den Legenden-Layouts (Glint <-> Shiro)\n"
        "Shift: Wechsel zwischen den Waffen-Layouts (Schwert/Schwert <-> Stab)\n"
        "F10: Soundausgabe aktivieren/deaktivieren\n\n"
        "Overlay-Funktionen:\n"
        "1. Ziehen des Overlays: Klicken und ziehen Sie das Overlay, um es zu verschieben.\n"
        "2. Sound: Sie können den Sound aktivieren oder deaktivieren.\n"
        "3. Farbänderung: Wenn eine Abklingzeit 5 Sekunden oder weniger beträgt, wird die Farbe rot.\n\n"
        "Hinweis: Um das Overlay zu schließen, verwenden Sie Alt+F4."
    )
    messagebox.showinfo("Overlay-Anleitung", instructions)


def generate_random_title():
    """Generiert einen zufälligen Titel für das Overlay."""
    titles = [
        "Magie im Fluss",
        "Krieger der Nacht",
        "Zauberhafte Kontrolle",
        "Stürmische Mächte",
        "Energie der Elemente",
        "Kraft der Dunkelheit",
        "Licht und Schatten",
        "Das Geheimnis der Magie",
        "Heroische Legenden",
        "Schicksalsweber"
    ]
    return random.choice(titles)


# Tkinter-Setup für Overlay
root = tk.Tk()
overlay_title = generate_random_title()  # Generiere einen zufälligen Titel
overlay = Overlay(root, overlay_title)  # Übergebe den Titel an das Overlay

# Anweisungen anzeigen, wenn das Programm gestartet wird
show_instructions()

# Threads starten
cooldown_thread = threading.Thread(target=check_cooldowns, daemon=True)
cooldown_thread.start()

overlay_thread = threading.Thread(target=overlay_loop, daemon=True)
overlay_thread.start()

monitor_thread = threading.Thread(target=monitor_screen, daemon=True)
monitor_thread.start()

with keyboard.Listener(on_press=on_press) as listener:
    root.mainloop()
    listener.join()
