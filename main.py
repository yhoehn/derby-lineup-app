import json
import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ListProperty, ObjectProperty, BooleanProperty, NumericProperty
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView

from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton

from kivy.core.window import Window
from kivy.utils import platform
from kivy.utils import platform

# Android Permissions
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE
    ])

# Verbesserte get_start_path für Android

# ---------------------------------------------------------
# Vollbild für Tablet / Desktop
# ---------------------------------------------------------
Window.fullscreen = "auto"

PLAYERS_FILE = "players.json"

# ---------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------
def load_json(file, default):
    if not os.path.exists(file):
        print(f"File {file} does not exist, using default")
        return default
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Successfully loaded {file}")
            return data
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {file}: {e}")
        return default
    except Exception as e:
        print(f"Error loading {file}: {e}")
        return default


def save_json(file, data):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {file}")
    except Exception as e:
        print(f"Error saving {file}: {e}")


def get_start_path():
    if platform == "android":
        from android.storage import primary_external_storage_path
        return primary_external_storage_path()
    return os.path.expanduser("~")


# ---------------------------------------------------------
# Player Card (TABLET VERSION – BIG & READABLE + DRAG & DROP)
# ---------------------------------------------------------
class PlayerCard(BoxLayout):
    is_being_dragged = BooleanProperty(False)
    drag_start_x = NumericProperty(0)
    drag_start_y = NumericProperty(0)
    
    def __init__(self, player, parent_layout, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.parent_layout = parent_layout

        self.size_hint_y = None
        self.height = 90  # GEÄNDERT: 72 -> 90 für mehr Platz
        self.orientation = "horizontal"
        self.padding = (12, 10)
        self.spacing = 10

        # Hintergrundfarbe basierend auf Status
        status = player.get("status", "NORMAL")
        bg_color = self._get_status_color(status)

        with self.canvas.before:
            self._bg_color = Color(*bg_color)
            self._bg_rect = RoundedRectangle(radius=[10])

        self.bind(pos=self._update_bg, size=self._update_bg)
        self.bind(is_being_dragged=self._update_opacity)

        # Status-Indikator (Icon statt Emoji - anklickbar)
        self.status_btn = MDIconButton(
            icon=self._get_status_icon(status),
            icon_size="28sp",
            theme_text_color="Custom",
            text_color=self._get_status_icon_color(status),
            on_release=lambda x: parent_layout.open_status_popup(self)
        )
        self.status_btn.size_hint_x = 0.08

        # Mittlerer Bereich (draggable)
        self.lbl = Label(
            text=f"{player['number']} – {player['name']} ({player['role']})",
            halign="left",
            valign="middle",
            font_size="22sp",
            size_hint_x=0.80,
            color=(0, 0, 0, 1),
        )
        self.lbl.bind(size=self.lbl.setter("text_size"))

        # Delete Button (nur im Player Pool sichtbar)
        self.del_btn = None
        if self._is_in_player_pool():
            self.del_btn = MDIconButton(
                icon="trash-can-outline",
                icon_size="28sp",
                on_release=lambda x: parent_layout.confirm_delete_player(player)
            )

        self.add_widget(self.status_btn)
        self.add_widget(self.lbl)
        if self.del_btn:
            self.add_widget(self.del_btn)

    def _get_status_color(self, status):
        """Gibt Hintergrundfarbe basierend auf Status zurück"""
        if status == "REST":
            return (1.0, 0.95, 0.7, 1)  # Gelblich
        elif status == "INJURED":
            return (1.0, 0.7, 0.7, 1)  # Rötlich
        else:  # NORMAL
            return (0.95, 0.95, 0.95, 1)  # Hellgrau

    def _is_in_player_pool(self):
        """Prüft ob Spieler*in nur im Player Pool ist (nicht in Boxen/Lines)"""
        player = self.player
        parent = self.parent_layout
        
        # Prüfe ob in irgendeiner Box/Line
        in_boxes = player in (
            parent.current_jammer + parent.next_jammer + parent.third_jammer +
            parent.line_a + parent.line_b + parent.line_c + 
            parent.penalty + parent.injured
        )
        
        return not in_boxes

    def _get_status_icon(self, status):
        """Gibt Icon basierend auf Status zurück"""
        if status == "REST":
            return "sleep"  # Oder "pause-circle"
        elif status == "INJURED":
            return "hospital-box"  # Oder "ambulance"
        else:  # NORMAL
            return "check-circle"

    def _get_status_icon_color(self, status):
        """Gibt Icon-Farbe basierend auf Status zurück"""
        if status == "REST":
            return (0.9, 0.7, 0.0, 1)  # Gelb
        elif status == "INJURED":
            return (0.9, 0.1, 0.1, 1)  # Rot
        else:  # NORMAL
            return (0.0, 0.7, 0.0, 1)  # Grün

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _update_opacity(self, instance, value):
        """Transparenz beim Dragging"""
        self.opacity = 0.5 if value else 1.0

    def on_touch_down(self, touch):
        # Delete-Button hat Priorität (falls vorhanden)
        if self.del_btn and self.del_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        # Status-Button hat Priorität
        if self.status_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        # Mittlerer Bereich (Label) → Drag starten ODER Popup
        if self.lbl.collide_point(*touch.pos):
            touch.grab(self)
            self.drag_start_x = touch.x
            self.drag_start_y = touch.y
            return True

        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            # Prüfe ob Bewegung groß genug für Drag (> 10 Pixel)
            dx = abs(touch.x - self.drag_start_x)
            dy = abs(touch.y - self.drag_start_y)
            
            if dx > 10 or dy > 10:
                if not self.is_being_dragged:
                    self.is_being_dragged = True
                    print(f"Drag started: {self.player['name']}")
            
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            
            if self.is_being_dragged:
                # Drag beenden - finde Drop-Zone
                self._handle_drop(touch)
                self.is_being_dragged = False
            else:
                # Kein Drag, nur Click → Popup öffnen
                self.parent_layout.open_assign_popup(self)
            
            return True
        return super().on_touch_up(touch)

    def _handle_drop(self, touch):
        """Findet Drop-Zone und führt Zuweisung durch"""
        # Finde welche Box unter dem Touch ist
        target_box = None
        target_name = None
        
        # Prüfe alle Boxen
        boxes = {
            'player_pool': self.parent_layout.ids.get('player_pool'),
            'current_jammer_box': self.parent_layout.ids.get('current_jammer_box'),
            'next_jammer_box': self.parent_layout.ids.get('next_jammer_box'),
            'third_jammer_box': self.parent_layout.ids.get('third_jammer_box'),
            'line_a_box': self.parent_layout.ids.get('line_a_box'),
            'line_b_box': self.parent_layout.ids.get('line_b_box'),
            'line_c_box': self.parent_layout.ids.get('line_c_box'),
            'penalty_box': self.parent_layout.ids.get('penalty_box'),
            'injured_box': self.parent_layout.ids.get('injured_box'),
        }
        
        for box_name, box_widget in boxes.items():
            if box_widget and box_widget.collide_point(*touch.pos):
                target_box = box_widget
                target_name = box_name
                break
        
        if target_name:
            print(f"Dropped {self.player['name']} on {target_name}")
            
            # Konvertiere box_name zu target für assign_to
            if target_name == 'player_pool':
                self.parent_layout.drop_to_player_pool(self.player)
            elif target_name.endswith('_box'):
                # Entferne '_box' suffix
                target = target_name.replace('_box', '')
                self.parent_layout.drop_assign_to(self.player, target)
        else:
            print(f"Dropped {self.player['name']} outside valid zone - no action")


# ---------------------------------------------------------
# Main Layout
# ---------------------------------------------------------
class MainLayout(BoxLayout):
    players = ListProperty([])

    current_jammer = ListProperty([])
    next_jammer = ListProperty([])
    third_jammer = ListProperty([])

    line_a = ListProperty([])
    line_b = ListProperty([])
    line_c = ListProperty([])

    penalty = ListProperty([])
    injured = ListProperty([])

    selected_player = ObjectProperty(None, allownone=True)

    # UNDO/REDO System
    history_stack = ListProperty([])
    history_index = NumericProperty(-1)

    # -----------------------------------------------------
    def on_kv_post(self, base_widget):
        raw_players = load_json(PLAYERS_FILE, []) or []
        
        # Migration: Füge "status" Feld hinzu falls nicht vorhanden
        self.players = []
        for player in raw_players:
            if "status" not in player:
                player["status"] = "NORMAL"
            self.players.append(player)
        
        # Speichere migrierte Daten
        if raw_players:
            self.save_players()
        
        self.update_ui()
        
        # Initialer Snapshot für Undo/Redo
        self._save_to_history()

    def save_players(self):
        save_json(PLAYERS_FILE, self.players)

    # -----------------------------------------------------
    # UNDO/REDO SYSTEM
    # -----------------------------------------------------
    def _create_snapshot(self):
        """Erstellt Snapshot des aktuellen Zustands"""
        import copy
        # Konvertiere ListProperty zu normalen Listen für deepcopy
        return {
            'current_jammer': copy.deepcopy(list(self.current_jammer)),
            'next_jammer': copy.deepcopy(list(self.next_jammer)),
            'third_jammer': copy.deepcopy(list(self.third_jammer)),
            'line_a': copy.deepcopy(list(self.line_a)),
            'line_b': copy.deepcopy(list(self.line_b)),
            'line_c': copy.deepcopy(list(self.line_c)),
            'penalty': copy.deepcopy(list(self.penalty)),
            'injured': copy.deepcopy(list(self.injured)),
            'players': copy.deepcopy(list(self.players))  # Für Status-Änderungen
        }

    def _save_to_history(self):
        """Speichert aktuellen Zustand in History"""
        snapshot = self._create_snapshot()
        
        # Entferne alle Schritte nach current index (bei neuer Änderung nach Undo)
        if self.history_index < len(self.history_stack) - 1:
            self.history_stack = self.history_stack[:self.history_index + 1]
        
        # Füge neuen Snapshot hinzu
        self.history_stack.append(snapshot)
        
        # Limit auf 20 Schritte
        if len(self.history_stack) > 20:
            self.history_stack.pop(0)
        else:
            self.history_index += 1
        
        print(f"History saved: {self.history_index + 1}/{len(self.history_stack)} steps")

    def _restore_snapshot(self, snapshot):
        """Stellt einen Snapshot wieder her"""
        import copy
        # ListProperty akzeptiert normale Listen als Zuweisung
        self.current_jammer = copy.deepcopy(snapshot['current_jammer'])
        self.next_jammer = copy.deepcopy(snapshot['next_jammer'])
        self.third_jammer = copy.deepcopy(snapshot['third_jammer'])
        self.line_a = copy.deepcopy(snapshot['line_a'])
        self.line_b = copy.deepcopy(snapshot['line_b'])
        self.line_c = copy.deepcopy(snapshot['line_c'])
        self.penalty = copy.deepcopy(snapshot['penalty'])
        self.injured = copy.deepcopy(snapshot['injured'])
        self.players = copy.deepcopy(snapshot['players'])
        
        self.save_players()
        self.update_ui()

    def undo(self):
        """Macht letzte Änderung rückgängig"""
        if self.history_index > 0:
            self.history_index -= 1
            snapshot = self.history_stack[self.history_index]
            self._restore_snapshot(snapshot)
            print(f"UNDO: Zurück zu Schritt {self.history_index + 1}/{len(self.history_stack)}")
            self.show_info_popup(f"Rückgängig: Schritt {self.history_index + 1}", duration=1.5)
        else:
            print("UNDO: Keine weiteren Schritte zurück")
            self.show_info_popup("Keine weiteren Schritte zurück", duration=1.5)

    def redo(self):
        """Stellt rückgängig gemachte Änderung wieder her"""
        if self.history_index < len(self.history_stack) - 1:
            self.history_index += 1
            snapshot = self.history_stack[self.history_index]
            self._restore_snapshot(snapshot)
            print(f"REDO: Vorwärts zu Schritt {self.history_index + 1}/{len(self.history_stack)}")
            self.show_info_popup(f"Wiederherstellen: Schritt {self.history_index + 1}", duration=1.5)
        else:
            print("REDO: Keine weiteren Schritte vorwärts")
            self.show_info_popup("Keine weiteren Schritte vorwärts", duration=1.5)

    # -----------------------------------------------------
    # DRAG & DROP HANDLERS
    # -----------------------------------------------------
    def drop_to_player_pool(self, player):
        """Spieler wird zurück in Player Pool gedropped"""
        # Prüfe ob Spieler*in in Injured Box ist
        was_injured = player in self.injured
        
        # Nur aus Lines/Jammer entfernen, NICHT aus Player Pool!
        for lst in (
            self.current_jammer, self.next_jammer, self.third_jammer,
            self.line_a, self.line_b, self.line_c, self.penalty, self.injured
        ):
            if player in lst:
                lst.remove(player)
        
        # Wenn aus Injured Box geholt: Status auf NORMAL setzen
        if was_injured:
            player["status"] = "NORMAL"
            self.save_players()
        
        self._save_to_history()
        self.update_ui()

    def drop_assign_to(self, player, target):
        """Spieler wird per Drag & Drop einer Box zugewiesen"""
        role = player["role"]

        # Rollenvalidierung
        if role == "J" and target in ("line_a", "line_b", "line_c"):
            print(f"Validation failed: Jammer can't be in Line")
            return
        if role != "J" and target in ("current_jammer", "next_jammer", "third_jammer"):
            print(f"Validation failed: Blocker/Pivot can't be Jammer")
            return

        # Jammer-Boxen dürfen nur 1 Jammer haben
        if target in ("current_jammer", "next_jammer", "third_jammer"):
            if getattr(self, target):
                print(f"Validation failed: Jammer box already full")
                return

        # Lines dürfen maximal 4 Spieler*innen haben
        if target in ("line_a", "line_b", "line_c"):
            lst = getattr(self, target)
            if len(lst) >= 4:
                print(f"Validation failed: Line already has 4 players")
                return
            # Maximal 1 Pivot pro Line
            if role == "P" and any(p["role"] == "P" for p in lst):
                print(f"Validation failed: Line already has a Pivot")
                return

        # Entfernen aus allen anderen Boxen (außer Player Pool)
        for lst in (
            self.current_jammer, self.next_jammer, self.third_jammer,
            self.line_a, self.line_b, self.line_c, self.penalty, self.injured
        ):
            if player in lst:
                lst.remove(player)

        # SPECIAL: Drop in Injured Box → Status auf INJURED setzen
        if target == "injured":
            if player["status"] != "INJURED":
                player["status"] = "INJURED"
                print(f"Status changed: {player['name']} → INJURED")

        getattr(self, target).append(player)
        self.save_players()
        self._save_to_history()
        self.update_ui()

    # -----------------------------------------------------
    # PHASE 2: Status-Management
    # -----------------------------------------------------
    def open_status_popup(self, card_widget):
        """Öffnet Popup zum Ändern des Spieler-Status"""
        player = card_widget.player
        
        layout = GridLayout(cols=1, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))
        
        popup = Popup(
            title=f"Status für {player['name']} ändern",
            content=layout,
            size_hint=(0.5, 0.4)
        )
        
        statuses = [
            ("✓ Normal (Spielbereit)", "NORMAL"),
            ("⏸ Rest (Pause)", "REST"),
            ("+ Injured (Verletzt)", "INJURED")
        ]
        
        for text, status in statuses:
            btn = Button(
                text=text,
                font_size="22sp",
                size_hint_y=None,
                height=70,
                on_release=lambda x, s=status, p=popup: self.change_player_status(player, s, p)
            )
            layout.add_widget(btn)
        
        popup.open()

    def change_player_status(self, player, new_status, popup):
        """Ändert den Status einer Spieler*in"""
        old_status = player.get("status", "NORMAL")
        player["status"] = new_status
        
        print(f"Status-Änderung: {player['name']} von {old_status} → {new_status}")
        
        # INJURED-Logik: Aus allen Lines/Jammer-Boxen entfernen, in Injured Box
        if new_status == "INJURED":
            # Aus Lines/Jammer entfernen (NICHT aus Player Pool!)
            for lst in (
                self.current_jammer, self.next_jammer, self.third_jammer,
                self.line_a, self.line_b, self.line_c, self.penalty
            ):
                if player in lst:
                    lst.remove(player)
            
            # In Injured Box hinzufügen (falls nicht schon drin)
            if player not in self.injured:
                self.injured.append(player)
        
        # Zurück von INJURED zu NORMAL/REST: Aus Injured Box entfernen + Auto-Assignment
        elif old_status == "INJURED" and new_status in ("NORMAL", "REST"):
            if player in self.injured:
                self.injured.remove(player)
                # Automatisch in nächste freie Box einfügen
                self._auto_assign_recovered_player(player)
        
        self.save_players()
        self._save_to_history()
        self.update_ui()
        popup.dismiss()
        
    def _auto_assign_recovered_player(self, player):
        """
        Weist einen Spieler automatisch einer freien Box zu nach Rückkehr von INJURED.
        
        Priorität für Jammer: Next → Third → Current
        Priorität für Blocker/Pivot: Next Line → Third Line → Current Line
        """
        role = player["role"]
        
        if role == "J":
            # Jammer: Suche freie Jammer-Box
            if not self.next_jammer:
                self.next_jammer.append(player)
                print(f"Auto-Assignment: {player['name']} → Next Jammer")
            elif not self.third_jammer:
                self.third_jammer.append(player)
                print(f"Auto-Assignment: {player['name']} → Third Jammer")
            elif not self.current_jammer:
                self.current_jammer.append(player)
                print(f"Auto-Assignment: {player['name']} → Current Jammer")
            else:
                print(f"Auto-Assignment: Alle Jammer-Boxen belegt, {player['name']} bleibt im Player Pool")
        
        else:  # Blocker oder Pivot
            # Suche Line mit Platz (max 4 Spieler*innen)
            for line_name, line_list in [("Next Line", self.line_b), ("Third Line", self.line_c), ("Current Line", self.line_a)]:
                if len(line_list) < 4:
                    # Prüfe Pivot-Regel (max 1 Pivot pro Line)
                    if role == "P" and any(p["role"] == "P" for p in line_list):
                        continue  # Diese Line hat schon einen Pivot
                    
                    line_list.append(player)
                    print(f"Auto-Assignment: {player['name']} → {line_name}")
                    return
            
            # Alle Lines voll
            print(f"Auto-Assignment: Alle Lines voll, {player['name']} bleibt im Player Pool")

    # -----------------------------------------------------
    # PHASE 1.1: Line-Validierung
    # -----------------------------------------------------
    def is_line_complete(self, line_list):
        """
        Prüft ob eine Line spielbar ist.
        
        Eine Line ist vollständig wenn:
        - Genau 4 Spieler*innen vorhanden sind UND
        - Maximal 1 Pivot dabei ist
        
        Returns:
            bool: True wenn Line spielbar, False wenn unvollständig
        """
        if len(line_list) != 4:
            return False
        
        pivot_count = sum(1 for p in line_list if p["role"] == "P")
        return pivot_count <= 1

    # -----------------------------------------------------
    def add_player(self, name, number, role):
        name = (name or "").strip()
        number = (number or "").strip()
        role = (role or "").strip().upper()

        if not name or not number or role not in ("J", "B", "P"):
            print(f"Invalid player input: name={name}, number={number}, role={role}")
            return

        # Neuer Spieler mit NORMAL Status
        self.players.append({
            "name": name,
            "number": number,
            "role": role,
            "status": "NORMAL"
        })
        self.save_players()
        
        # Input-Felder leeren nach erfolgreichem Hinzufügen
        self.ids.in_name.text = ""
        self.ids.in_number.text = ""
        self.ids.in_role.text = ""
        
        self._save_to_history()
        self.update_ui()

    # -----------------------------------------------------
    def confirm_delete_player(self, player):
        """Zeigt Bestätigungsdialog bevor Spieler*in gelöscht wird"""
        content = BoxLayout(orientation="vertical", spacing=20, padding=20)
        
        msg = Label(
            text=f"Möchtest du {player['name']} wirklich löschen?",
            font_size="20sp",
            size_hint_y=0.6
        )
        
        btn_box = BoxLayout(spacing=10, size_hint_y=0.4)
        
        popup = Popup(
            title="Spieler*in löschen?",
            content=content,
            size_hint=(0.6, 0.3)
        )
        
        yes_btn = Button(
            text="Ja",
            font_size="22sp",
            on_release=lambda x: self._delete_player_confirmed(player, popup)
        )
        
        no_btn = Button(
            text="Nein",
            font_size="22sp",
            on_release=popup.dismiss
        )
        
        btn_box.add_widget(no_btn)
        btn_box.add_widget(yes_btn)
        
        content.add_widget(msg)
        content.add_widget(btn_box)
        
        popup.open()

    def _delete_player_confirmed(self, player, popup):
        """Führt das Löschen nach Bestätigung aus"""
        self.delete_player(player)
        popup.dismiss()

    def delete_player(self, player):
        if player in self.players:
            self.players.remove(player)

        # Aus allen Boxen entfernen
        for lst in (
            self.current_jammer, self.next_jammer, self.third_jammer,
            self.line_a, self.line_b, self.line_c, self.penalty, self.injured
        ):
            if player in lst:
                lst.remove(player)

        self.save_players()
        self._save_to_history()
        self.update_ui()

    # -----------------------------------------------------
    # Assignment popup (bleibt als Alternative zu Drag & Drop)
    # -----------------------------------------------------
    def open_assign_popup(self, card_widget):
        player = card_widget.player
        role = player["role"]

        layout = GridLayout(cols=1, spacing=10, padding=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        targets = []

        if player in (
            self.current_jammer + self.next_jammer + self.third_jammer +
            self.line_a + self.line_b + self.line_c + self.penalty + self.injured
        ):
            targets.append(("Zurück in Playerpool", "player_pool"))

        if role == "J":
            for t in ("current_jammer", "next_jammer", "third_jammer", "penalty"):
                if player not in getattr(self, t):
                    targets.append((t.replace("_", " ").title(), t))
        else:
            for t in ("line_a", "line_b", "line_c", "penalty"):
                if player not in getattr(self, t):
                    targets.append((t.replace("_", " ").title(), t))

        popup = Popup(title=f"{player['name']} zuordnen", size_hint=(0.6, 0.7))

        for txt, target in targets:
            layout.add_widget(
                Button(
                    text=txt,
                    size_hint_y=None,
                    height=70,
                    font_size="22sp",
                    on_release=lambda x, t=target, p=popup:
                    self.assign_or_return(player, t, p)
                )
            )

        popup.content = layout
        popup.open()

    def assign_or_return(self, player, target, popup):
        if target == "player_pool":
            self.drop_to_player_pool(player)
        else:
            self.drop_assign_to(player, target)

        popup.dismiss()

    # -----------------------------------------------------
    # PHASE 1.3-1.5: AUTO-FILL LOGIK
    # -----------------------------------------------------
    def fill_current_line(self):
        """
        FILL Button Handler: Füllt Current Line automatisch auf.
        """
        if self.is_line_complete(self.line_a):
            self.show_info_popup("Current Line ist bereits vollständig!")
            return
        
        success = self.auto_fill_current_line()
        
        if success:
            self._save_to_history()
            self.show_info_popup("Current Line wurde aufgefüllt!", duration=2)
        else:
            self.show_info_popup("Keine Ersatzspieler*innen in Next/Third Line verfügbar!")

    def auto_fill_current_line(self):
        """
        Füllt Current Line automatisch mit Spieler*innen aus Next/Third Line.
        
        Priorität:
        1. Pivot holen (falls keiner in Current Line)
        2. Blocker auffüllen bis 4 Spieler*innen
        
        Quell-Priorität: Next Line (B) → Third Line (C)
        
        Returns:
            bool: True wenn erfolgreich aufgefüllt, False wenn nicht genug Ersatz
        """
        missing = 4 - len(self.line_a)
        if missing <= 0:
            return True  # Bereits voll
        
        print(f"Auto-Fill: {missing} Spieler*innen fehlen in Current Line")
        
        # Prüfe ob Pivot fehlt
        has_pivot = any(p["role"] == "P" for p in self.line_a)
        needs_pivot = not has_pivot
        
        filled = 0
        
        # SCHRITT 1: Pivot holen (falls benötigt)
        if needs_pivot:
            pivot = self._find_player_in_lines("P")
            if pivot:
                source_line = pivot["source"]
                player = pivot["player"]
                
                print(f"Auto-Fill: Nehme Pivot {player['name']} aus {source_line}")
                
                # Aus Quell-Line entfernen
                getattr(self, source_line).remove(player)
                # Zu Current Line hinzufügen
                self.line_a.append(player)
                
                filled += 1
                missing -= 1
        
        # SCHRITT 2: Blocker auffüllen
        while missing > 0:
            blocker = self._find_player_in_lines("B")
            if not blocker:
                break  # Keine Blocker mehr verfügbar
            
            source_line = blocker["source"]
            player = blocker["player"]
            
            print(f"Auto-Fill: Nehme Blocker {player['name']} aus {source_line}")
            
            # Aus Quell-Line entfernen
            getattr(self, source_line).remove(player)
            # Zu Current Line hinzufügen
            self.line_a.append(player)
            
            filled += 1
            missing -= 1
        
        self.update_ui()
        
        # Erfolgreich wenn Current Line jetzt vollständig ist
        success = self.is_line_complete(self.line_a)
        
        if success:
            print(f"Auto-Fill: Erfolgreich! {filled} Spieler*innen verschoben")
        else:
            print(f"Auto-Fill: Nur {filled} Spieler*innen gefunden, Current Line noch unvollständig")
        
        return success

    def _find_player_in_lines(self, role):
        # Priorität 1: Next Line (B)
        for player in self.line_b:
            # REST-Spieler überspringen
            if player.get("status") == "REST":
                continue
            if player["role"] == role:
                return {"source": "line_b", "player": player}
        
        # Priorität 2: Third Line (C)
        for player in self.line_c:
            # REST-Spieler überspringen
            if player.get("status") == "REST":
                continue
            if player["role"] == role:
                return {"source": "line_c", "player": player}
        
        return None

    def show_info_popup(self, message, duration=3):
        """
        Zeigt eine Info-Nachricht für kurze Zeit an.
        """
        content = Label(
            text=message,
            font_size="20sp",
            halign="center",
            valign="middle"
        )
        content.bind(size=content.setter("text_size"))
        
        popup = Popup(
            title="Info",
            content=content,
            size_hint=(0.6, 0.25),
            auto_dismiss=True
        )
        
        popup.open()
        
        # Auto-close nach X Sekunden
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: popup.dismiss(), duration)

    # -----------------------------------------------------
    # INTELLIGENTE ROTATION (Phase 1 - verbessert)
    # -----------------------------------------------------
    def rotate_lineup(self):
        """
        Intelligente Rotation: Rotiert nur zwischen tatsächlich belegten Boxen.
        
        Jammer und Lines werden unabhängig voneinander rotiert:
        - 2 belegte Jammer-Slots → 2er-Rotation
        - 3 belegte Jammer-Slots → 3er-Rotation
        - 2 belegte Line-Slots → 2er-Rotation  
        - 3 belegte Line-Slots → 3er-Rotation
        
        Current Line muss vollständig sein, sonst Warnung.
        REST-Spieler werden übersprungen und automatisch ersetzt.
        """
        # PHASE 1.2: Check ob Current Line vollständig ist
        if not self.is_line_complete(self.line_a):
            self.show_incomplete_line_warning()
            return  # Rotation wird NICHT ausgeführt
        
        # ========== JAMMER ROTATION (unabhängig) ==========
        self._rotate_jammers()
        
        # ========== LINE ROTATION (unabhängig) ==========
        self._rotate_lines()
        
        # NEU: Auto-Fill wenn Current Line durch REST-Filter unvollständig wurde
        if len(self.line_a) < 4:
            print(f"Current Line nach Rotation unvollständig ({len(self.line_a)}/4) - fülle automatisch auf")
            self.auto_fill_current_line()
        
        # Prüfe ob Current Jammer leer ist (REST wurde übersprungen)
        if not self.current_jammer:
            # Versuche Jammer aus Next zu holen
            if self.next_jammer and self.next_jammer[0].get("status") != "REST":
                jammer = self.next_jammer.pop(0)
                self.current_jammer.append(jammer)
                print(f"Current Jammer war leer - {jammer['name']} aus Next geholt")
            elif self.third_jammer and self.third_jammer[0].get("status") != "REST":
                jammer = self.third_jammer.pop(0)
                self.current_jammer.append(jammer)
                print(f"Current Jammer war leer - {jammer['name']} aus Third geholt")
        
        self._save_to_history()
        self.update_ui()

    def _rotate_jammers(self):
        """
        Rotiert nur zwischen belegten Jammer-Slots.
        """
        # Sammle belegte Jammer-Slots
        jammer_map = {}
        if self.current_jammer:
            jammer_map['current'] = self.current_jammer[0]  # Liste hat max. 1 Element
        if self.next_jammer:
            jammer_map['next'] = self.next_jammer[0]
        if self.third_jammer:
            jammer_map['third'] = self.third_jammer[0]
        
        # Anzahl belegter Slots
        count = len(jammer_map)
        
        if count == 0:
            # Keine Jammer → nichts tun
            return
        
        elif count == 1:
            # Nur 1 Jammer → keine Rotation möglich
            return
        
        elif count == 2:
            # 2-Wege-Rotation zwischen den beiden belegten Slots
            slots = list(jammer_map.keys())
            slot_a, slot_b = slots[0], slots[1]
            
            jammer_a = jammer_map[slot_a]
            jammer_b = jammer_map[slot_b]
            
            # Leere alle
            self.current_jammer.clear()
            self.next_jammer.clear()
            self.third_jammer.clear()
            
            # Setze getauscht (mit REST-Filter für Current)
            if slot_a == 'current':
                # Jammer B wird zu Current → prüfe REST
                if jammer_b.get("status") != "REST":
                    self.current_jammer.append(jammer_b)
                else:
                    # REST bleibt in ursprünglicher Position
                    if slot_b == 'next':
                        self.next_jammer.append(jammer_b)
                    else:
                        self.third_jammer.append(jammer_b)
                    print(f"REST-Jammer bleibt: {jammer_b['name']}")
            elif slot_a == 'next':
                self.next_jammer.append(jammer_b)
            else:  # third
                self.third_jammer.append(jammer_b)
            
            if slot_b == 'current':
                # Jammer A wird zu Current → prüfe REST
                if jammer_a.get("status") != "REST":
                    self.current_jammer.append(jammer_a)
                else:
                    # REST bleibt in ursprünglicher Position
                    if slot_a == 'next':
                        self.next_jammer.append(jammer_a)
                    else:
                        self.third_jammer.append(jammer_a)
                    print(f"REST-Jammer bleibt: {jammer_a['name']}")
            elif slot_b == 'next':
                self.next_jammer.append(jammer_a)
            else:  # third
                self.third_jammer.append(jammer_a)
        
        elif count == 3:
            # 3-Wege-Rotation: Current → Third → Next → Current
            # (Rückwärts im Vergleich zu Lines)
            jammer_current = jammer_map['current']
            jammer_next = jammer_map['next']
            jammer_third = jammer_map['third']
            
            self.current_jammer.clear()
            self.next_jammer.clear()
            self.third_jammer.clear()
            
            # Current → Third
            self.third_jammer.append(jammer_current)
            # Third → Next
            self.next_jammer.append(jammer_third)
            # Next → Current (nur wenn NICHT REST)
            if jammer_next.get("status") != "REST":
                self.current_jammer.append(jammer_next)
            else:
                # REST-Jammer bleibt in Next
                self.next_jammer.append(jammer_next)
                print(f"REST-Jammer bleibt in Next: {jammer_next['name']}")

    def _rotate_lines(self):
        """
        Rotiert nur zwischen belegten Line-Slots.
        """
        # Sammle belegte Line-Slots
        line_map = {}
        if self.line_a:
            line_map['a'] = list(self.line_a)  # Kopie der Liste
        if self.line_b:
            line_map['b'] = list(self.line_b)
        if self.line_c:
            line_map['c'] = list(self.line_c)
        
        # Anzahl belegter Slots
        count = len(line_map)
        
        if count == 0:
            # Keine Lines → nichts tun
            return
        
        elif count == 1:
            # Nur 1 Line → keine Rotation möglich
            return
        
        elif count == 2:
            # 2-Wege-Rotation zwischen den beiden belegten Slots
            slots = list(line_map.keys())
            slot_a, slot_b = slots[0], slots[1]
            
            # Originale Listen
            line_players_a = line_map[slot_a]
            line_players_b = line_map[slot_b]
            
            # Filtere REST-Spieler aus der Line die zu Current (A) wird
            if slot_a == 'a':
                # Line B wird zu Current A → filtere REST
                line_b_normal = [p for p in line_players_b if p.get("status") != "REST"]
                line_b_rest = [p for p in line_players_b if p.get("status") == "REST"]
            else:
                line_b_normal = line_players_b
                line_b_rest = []
            
            if slot_b == 'a':
                # Line A wird zu Current A → filtere REST
                line_a_normal = [p for p in line_players_a if p.get("status") != "REST"]
                line_a_rest = [p for p in line_players_a if p.get("status") == "REST"]
            else:
                line_a_normal = line_players_a
                line_a_rest = []
            
            # Leere alle
            self.line_a.clear()
            self.line_b.clear()
            self.line_c.clear()
            
            # Setze getauscht (mit REST-Filter)
            if slot_a == 'a':
                self.line_a.extend(line_b_normal)
                # REST-Spieler bleiben in ihrer ursprünglichen Line
                if line_b_rest:
                    if slot_b == 'b':
                        self.line_b.extend(line_b_rest)
                    elif slot_b == 'c':
                        self.line_c.extend(line_b_rest)
            elif slot_a == 'b':
                self.line_b.extend(line_b_normal)
            else:  # c
                self.line_c.extend(line_b_normal)
            
            if slot_b == 'a':
                self.line_a.extend(line_a_normal)
                # REST-Spieler bleiben in ihrer ursprünglichen Line
                if line_a_rest:
                    if slot_a == 'b':
                        self.line_b.extend(line_a_rest)
                    elif slot_a == 'c':
                        self.line_c.extend(line_a_rest)
            elif slot_b == 'b':
                self.line_b.extend(line_a_normal)
            else:  # c
                self.line_c.extend(line_a_normal)
        
        elif count == 3:
            # 3-Wege-Rotation: A → C → B → A (rückwärts)
            line_a_players = list(self.line_a)
            line_b_players = list(self.line_b)
            line_c_players = list(self.line_c)
            
            # REST-Spieler aus Line B filtern (würden nach Current kommen)
            line_b_normal = [p for p in line_b_players if p.get("status") != "REST"]
            line_b_rest = [p for p in line_b_players if p.get("status") == "REST"]
            
            self.line_a.clear()
            self.line_b.clear()
            self.line_c.clear()
            
            # A → C
            self.line_c.extend(line_a_players)
            # C → B (inkl. REST-Spieler die dort bleiben)
            self.line_b.extend(line_c_players)
            self.line_b.extend(line_b_rest)  # REST-Spieler bleiben in Next
            # B → A (nur NORMAL-Spieler)
            self.line_a.extend(line_b_normal)
            
            if line_b_rest:
                print(f"REST-Spieler bleiben in Next Line: {[p['name'] for p in line_b_rest]}")

    def show_incomplete_line_warning(self):
        """
        Zeigt Warnung wenn Current Line unvollständig ist.
        User kann:
        - Auto-Fill & Rotieren (füllt auf + rotiert)
        - Trotzdem rotieren (ohne auffüllen)
        - Abbrechen
        """
        content = BoxLayout(orientation="vertical", spacing=20, padding=20)
        
        # Detaillierte Info über Current Line
        line_info = self.get_line_info(self.line_a)
        
        msg = Label(
            text=f"Current Line ist unvollständig!\n\n{line_info}",
            font_size="20sp",
            size_hint_y=0.5,
            halign="center",
            valign="middle"
        )
        msg.bind(size=msg.setter("text_size"))
        
        btn_box = BoxLayout(spacing=10, size_hint_y=0.5, orientation="vertical")
        
        popup = Popup(
            title="⚠️ Line unvollständig",
            content=content,
            size_hint=(0.7, 0.5)
        )
        
        # Button 1: Auto-Fill & Rotieren
        autofill_btn = Button(
            text="Auto-Fill & Rotieren",
            font_size="22sp",
            on_release=lambda x: self._autofill_and_rotate(popup)
        )
        
        # Button 2: Trotzdem rotieren (ohne Fill)
        force_btn = Button(
            text="Trotzdem rotieren",
            font_size="22sp",
            on_release=lambda x: self._force_rotate(popup)
        )
        
        # Button 3: Abbrechen
        cancel_btn = Button(
            text="Abbrechen",
            font_size="22sp",
            on_release=popup.dismiss
        )
        
        btn_box.add_widget(autofill_btn)
        btn_box.add_widget(force_btn)
        btn_box.add_widget(cancel_btn)
        
        content.add_widget(msg)
        content.add_widget(btn_box)
        
        popup.open()

    def _autofill_and_rotate(self, popup):
        """
        Füllt Current Line auf und rotiert danach.
        """
        popup.dismiss()
        
        # Versuche aufzufüllen
        success = self.auto_fill_current_line()
        
        if success:
            # Erfolgreich aufgefüllt → Rotieren
            self._rotate_jammers()
            self._rotate_lines()
            self._save_to_history()
            self.update_ui()
            self.show_info_popup("Line aufgefüllt & rotiert!", duration=2)
        else:
            # Konnte nicht auffüllen
            self.show_info_popup("Keine Ersatzspieler*innen verfügbar!\nRotation abgebrochen.")

    def get_line_info(self, line_list):
        """
        Gibt detaillierte Info über eine Line zurück.
        """
        count = len(line_list)
        pivot_count = sum(1 for p in line_list if p["role"] == "P")
        blocker_count = sum(1 for p in line_list if p["role"] == "B")
        
        info = f"Aktuell: {count}/4 Spieler*innen\n"
        info += f"Blocker: {blocker_count}, Pivot: {pivot_count}\n"
        
        if count < 4:
            missing = 4 - count
            info += f"Fehlend: {missing} Spieler*innen"
        elif pivot_count > 1:
            info += f"Problem: Zu viele Pivots ({pivot_count})"
        
        return info

    def _force_rotate(self, popup):
        """
        Führt Rotation aus auch wenn Current Line unvollständig ist.
        """
        popup.dismiss()
        
        # Rotation ohne Check durchführen
        self._rotate_jammers()
        self._rotate_lines()
        
        self._save_to_history()
        self.update_ui()

    # -----------------------------------------------------
    def confirm_clear_boxes(self):
        """Zeigt Bestätigungsdialog bevor alle Boxen geleert werden"""
        content = BoxLayout(orientation="vertical", spacing=20, padding=20)
        
        msg = Label(
            text="Möchtest du wirklich alle Zuweisungen löschen?",
            font_size="20sp",
            size_hint_y=0.6
        )
        
        btn_box = BoxLayout(spacing=10, size_hint_y=0.4)
        
        popup = Popup(
            title="Alle Boxen leeren?",
            content=content,
            size_hint=(0.6, 0.3)
        )
        
        yes_btn = Button(
            text="Ja",
            font_size="22sp",
            on_release=lambda x: self._clear_boxes_confirmed(popup)
        )
        
        no_btn = Button(
            text="Nein",
            font_size="22sp",
            on_release=popup.dismiss
        )
        
        btn_box.add_widget(no_btn)
        btn_box.add_widget(yes_btn)
        
        content.add_widget(msg)
        content.add_widget(btn_box)
        
        popup.open()

    def _clear_boxes_confirmed(self, popup):
        """Führt das Leeren nach Bestätigung aus"""
        self.clear_boxes()
        popup.dismiss()

    def clear_boxes(self):
        self.current_jammer.clear()
        self.next_jammer.clear()
        self.third_jammer.clear()
        self.line_a.clear()
        self.line_b.clear()
        self.line_c.clear()
        self.penalty.clear()
        self.injured.clear()
        self._save_to_history()
        self.update_ui()

    # -----------------------------------------------------
    # IMPORT JSON (mit Lineup-Support)
    # -----------------------------------------------------
    def import_players_json(self):
        chooser = FileChooserListView(
            filters=["*.json"],
            path=get_start_path(),
            size_hint=(1, 1)
        )

        scroll = ScrollView()
        scroll.add_widget(chooser)

        popup = Popup(
            title="JSON-Datei auswählen (Spieler oder Lineup)",
            content=scroll,
            size_hint=(0.9, 0.9)
        )

        def load_file(instance, selection, touch):
            if not selection:
                return
            data = load_json(selection[0], None)
            
            if data is None:
                print(f"Fehler beim Laden von {selection[0]}")
                return
            
            # FALL 1: Neue Struktur mit "players" und "assignments"
            if isinstance(data, dict) and "players" in data:
                # Migration beim Import
                for player in data["players"]:
                    if "status" not in player:
                        player["status"] = "NORMAL"
                
                self.players = data["players"]
                
                # Lade Zuweisungen (falls vorhanden)
                if "assignments" in data:
                    assignments = data["assignments"]
                    # Direkte Zuweisung ohne deepcopy - ListProperty kann Listen zuweisen
                    self.current_jammer = list(assignments.get('current_jammer', []))
                    self.next_jammer = list(assignments.get('next_jammer', []))
                    self.third_jammer = list(assignments.get('third_jammer', []))
                    self.line_a = list(assignments.get('line_a', []))
                    self.line_b = list(assignments.get('line_b', []))
                    self.line_c = list(assignments.get('line_c', []))
                    self.penalty = list(assignments.get('penalty', []))
                    self.injured = list(assignments.get('injured', []))
                    print("✓ Lineup (Spieler + Zuweisungen) importiert")
                else:
                    # Nur Spieler, keine Zuweisungen
                    self.clear_boxes()
                    print("✓ Nur Spieler importiert (keine Zuweisungen)")
                
                self.save_players()
                self._save_to_history()
                self.update_ui()
                popup.dismiss()
                self.show_info_popup("Import erfolgreich!", duration=2)
            
            # FALL 2: Alte Struktur - einfache Liste von Spielern
            elif isinstance(data, list):
                # Migration beim Import
                for player in data:
                    if "status" not in player:
                        player["status"] = "NORMAL"
                
                self.players = data
                self.clear_boxes()
                self.save_players()
                self._save_to_history()
                self.update_ui()
                popup.dismiss()
                print("✓ Spieler-Liste importiert (alte Struktur)")
                self.show_info_popup("Spieler importiert!", duration=2)
            
            else:
                print(f"Ungültiges JSON-Format in {selection[0]}")
                self.show_info_popup("Ungültiges Dateiformat!")

        chooser.bind(on_submit=load_file)
        popup.open()

    # -----------------------------------------------------
    # EXPORT JSON (mit Lineup-Support)
    # -----------------------------------------------------
    def export_players_json(self):
        from kivy.uix.textinput import TextInput
        
        content = BoxLayout(orientation="vertical", spacing=15, padding=15)
        
        # Info-Text
        info = Label(
            text="Wähle was exportiert werden soll:",
            font_size="22sp",
            size_hint_y=None,
            height=40
        )
        
        # Filename Input
        filename_box = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=60)
        filename_input = TextInput(
            text="lineup_export.json",
            font_size="20sp",
            multiline=False
        )
        filename_box.add_widget(Label(text="Dateiname:", size_hint_x=0.3, font_size="20sp"))
        filename_box.add_widget(filename_input)
        
        # Export-Optionen
        export_options = GridLayout(cols=1, spacing=10, size_hint_y=None, height=200)
        
        popup = Popup(
            title="Export Optionen",
            content=content,
            size_hint=(0.7, 0.6)
        )
        
        # Option 1: Nur Spieler
        btn_players_only = Button(
            text="Nur Spieler\n(ohne Zuweisungen)",
            font_size="20sp",
            size_hint_y=None,
            height=60,
            on_release=lambda x: self._export_players_only(filename_input.text, popup)
        )
        
        # Option 2: Komplettes Lineup
        btn_full_lineup = Button(
            text="Komplettes Lineup\n(Spieler + Zuweisungen)",
            font_size="20sp",
            size_hint_y=None,
            height=60,
            on_release=lambda x: self._export_full_lineup(filename_input.text, popup)
        )
        
        export_options.add_widget(btn_players_only)
        export_options.add_widget(btn_full_lineup)
        
        content.add_widget(info)
        content.add_widget(filename_box)
        content.add_widget(export_options)
        
        popup.open()

    def _export_players_only(self, filename, popup):
        """Exportiert nur Spieler-Liste"""
        filename = (filename or "players_export.json").strip()
        if not filename.endswith('.json'):
            filename += '.json'
        
        chooser = FileChooserListView(
            path=get_start_path(),
            dirselect=True,
            size_hint=(1, 1)
        )

        scroll = ScrollView()
        scroll.add_widget(chooser)

        dir_popup = Popup(
            title="Export-Zielordner wählen",
            content=scroll,
            size_hint=(0.9, 0.9)
        )

        def save_file(instance, selection, touch):
            if not selection:
                return
            target_dir = selection[0]
            if not os.path.isdir(target_dir):
                return
            
            # Nur Spieler exportieren
            save_json(os.path.join(target_dir, filename), self.players)
            print(f"✓ Nur Spieler exportiert: {filename}")
            self.show_info_popup(f"Spieler exportiert:\n{filename}", duration=2)
            dir_popup.dismiss()
            popup.dismiss()

        chooser.bind(on_submit=save_file)
        dir_popup.open()

    def _export_full_lineup(self, filename, popup):
        """Exportiert komplettes Lineup (Spieler + Zuweisungen)"""
        filename = (filename or "lineup_export.json").strip()
        if not filename.endswith('.json'):
            filename += '.json'
        
        chooser = FileChooserListView(
            path=get_start_path(),
            dirselect=True,
            size_hint=(1, 1)
        )

        scroll = ScrollView()
        scroll.add_widget(chooser)

        dir_popup = Popup(
            title="Export-Zielordner wählen",
            content=scroll,
            size_hint=(0.9, 0.9)
        )

        def save_file(instance, selection, touch):
            if not selection:
                return
            target_dir = selection[0]
            if not os.path.isdir(target_dir):
                return
            
            # Komplettes Lineup exportieren
            export_data = {
                "players": self.players,
                "assignments": {
                    "current_jammer": self.current_jammer,
                    "next_jammer": self.next_jammer,
                    "third_jammer": self.third_jammer,
                    "line_a": self.line_a,
                    "line_b": self.line_b,
                    "line_c": self.line_c,
                    "penalty": self.penalty,
                    "injured": self.injured
                }
            }
            
            save_json(os.path.join(target_dir, filename), export_data)
            print(f"✓ Komplettes Lineup exportiert: {filename}")
            self.show_info_popup(f"Lineup exportiert:\n{filename}", duration=2)
            dir_popup.dismiss()
            popup.dismiss()

        chooser.bind(on_submit=save_file)
        dir_popup.open()

    # -----------------------------------------------------
    def update_ui(self):
        if not self.ids:
            return

        def fill(box_id, data):
            box = self.ids.get(box_id)
            if box:
                box.clear_widgets()
                for p in data:
                    box.add_widget(PlayerCard(p, self))

        self.ids.player_pool.clear_widgets()
        for p in self.players:
            self.ids.player_pool.add_widget(PlayerCard(p, self))

        fill("current_jammer_box", self.current_jammer)
        fill("next_jammer_box", self.next_jammer)
        fill("third_jammer_box", self.third_jammer)
        fill("line_a_box", self.line_a)
        fill("line_b_box", self.line_b)
        fill("line_c_box", self.line_c)
        fill("penalty_box", self.penalty)
        fill("injured_box", self.injured)


# ---------------------------------------------------------
class DerbyApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        return MainLayout()


if __name__ == "__main__":
    DerbyApp().run()