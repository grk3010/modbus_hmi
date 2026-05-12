import asyncio
import os
import subprocess
from nicegui import ui
from shared_state import settings, save_settings

class KeyboardDialog(ui.dialog):
    def __init__(self, title, initial_value='', on_save=None):
        super().__init__()
        self.input_data = initial_value
        self.on_save = on_save
        self.caps = False
        
        with self, ui.card().classes('w-[850px] max-w-[95vw] bg-[#1a1c1e] text-white border-2 border-primary shadow-2xl'):
            ui.label(title).classes('text-h6 font-bold text-primary q-mb-sm')
            self.display = ui.input(value=self.input_data).props('dark outlined readonly fill-mask').classes('w-full text-h5 q-mb-md')
            
            with ui.column().classes('w-full gap-1'):
                # Define layouts
                self.rows = [
                    ['1','2','3','4','5','6','7','8','9','0','-','='],
                    ['q','w','e','r','t','y','u','i','o','p','[',']'],
                    ['a','s','d','f','g','h','j','k','l',';',"'"],
                    ['z','x','c','v','b','n','m',',','.','/']
                ]
                
                self.key_container = ui.column().classes('w-full gap-1')
                self._draw_keys()
                
                with ui.row().classes('w-full justify-between q-mt-md'):
                    with ui.row().classes('gap-2'):
                        ui.button('SPACE', on_click=lambda: self._press(' ')).props('flat bg-grey-9 text-white').classes('w-48')
                        ui.button(icon='backspace', on_click=self._backspace).props('flat bg-orange-9 text-white').classes('w-20')
                    with ui.row().classes('gap-2'):
                        ui.button('CANCEL', on_click=self.close).props('flat text-grey')
                        ui.button('OK', on_click=self._submit).props('color=primary text-white').classes('px-8')

    def _draw_keys(self):
        self.key_container.clear()
        with self.key_container:
            for row in self.rows:
                with ui.row().classes('w-full justify-center gap-1 no-wrap'):
                    if row == self.rows[2]: # A row
                        ui.button('CAPS', on_click=self._toggle_caps).props(f'flat {"bg-primary" if self.caps else "bg-grey-9"} text-white').classes('w-16 h-12')
                    for key in row:
                        val = key.upper() if self.caps else key
                        ui.button(val, on_click=lambda k=val: self._press(k)).props('flat bg-grey-9 text-white').classes('w-10 h-12 text-bold')

    def _toggle_caps(self):
        self.caps = not self.caps
        self._draw_keys()

    def _press(self, key):
        self.input_data += key
        self.display.value = self.input_data

    def _backspace(self):
        self.input_data = self.input_data[:-1]
        self.display.value = self.input_data

    def _submit(self):
        if self.on_save:
            self.on_save(self.input_data)
        self.close()

class NumpadDialog(ui.dialog):
    def __init__(self, title, initial_value=0.0, on_save=None):
        super().__init__()
        self.input_data = str(initial_value)
        self.on_save = on_save
        
        with self, ui.card().classes('w-80 bg-[#1a1c1e] text-white border-2 border-indigo-500 shadow-2xl items-center'):
            ui.label(title).classes('text-h6 font-bold text-indigo-400 q-mb-sm')
            self.display = ui.label(self.input_data).classes('text-h3 font-mono bg-black/40 w-full text-right q-pa-md rounded border border-gray-700 q-mb-md')
            
            # Numeric Grid
            grid = [
                ['7', '8', '9'],
                ['4', '5', '6'],
                ['1', '2', '3'],
                ['.', '0', '⌫']
            ]
            
            with ui.column().classes('w-full gap-2'):
                for row in grid:
                    with ui.row().classes('w-full justify-around gap-2 no-wrap'):
                        for key in row:
                            if key == '⌫':
                                ui.button(key, on_click=self._backspace).props('flat bg-orange-9 text-white text-h5').classes('w-20 h-16')
                            else:
                                ui.button(key, on_click=lambda k=key: self._press(k)).props('flat bg-grey-9 text-white text-h5').classes('w-20 h-16')
                
                with ui.row().classes('w-full justify-between q-mt-md px-2'):
                    ui.button('CLEAR', on_click=self._clear).props('flat color=grey-5')
                    ui.button('CANCEL', on_click=self.close).props('flat color=grey-5')
                    ui.button('OK', on_click=self._submit).props('color=indigo text-white').classes('px-6')

    def _press(self, key):
        if key == '.' and '.' in self.input_data:
            return
        if self.input_data == '0' and key != '.':
            self.input_data = key
        else:
            self.input_data += key
        self.display.set_text(self.input_data)

    def _backspace(self):
        self.input_data = self.input_data[:-1]
        if not self.input_data: self.input_data = '0'
        self.display.set_text(self.input_data)

    def _clear(self):
        self.input_data = '0'
        self.display.set_text(self.input_data)

    def _submit(self):
        if self.on_save:
            try:
                self.on_save(float(self.input_data))
            except ValueError:
                self.on_save(0.0)
        self.close()

class KeyboardInput(ui.input):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on('click', self._open_keyboard)
        self.props('readonly cursor-pointer') # Prevent native keyboard on HMI

    def _open_keyboard(self):
        KeyboardDialog(self._props.get('label') or "Enter Text", initial_value=self.value, on_save=self._update_val).open()
    
    def _update_val(self, new_val):
        self.value = new_val

class NumberInput(ui.number):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on('click', self._open_numpad)
        self.props('readonly cursor-pointer')

    def _open_numpad(self):
        NumpadDialog(self._props.get('label') or "Enter Value", initial_value=self.value or 0, on_save=self._update_val).open()

    def _update_val(self, new_val):
        self.value = new_val

class IPNumpadDialog(ui.dialog):
    """Numpad dialog for entering IP addresses (allows multiple dots, returns string)."""
    def __init__(self, title, initial_value='', on_save=None):
        super().__init__()
        self.input_data = str(initial_value)
        self.on_save = on_save
        
        with self, ui.card().classes('w-80 bg-[#1a1c1e] text-white border-2 border-indigo-500 shadow-2xl items-center'):
            ui.label(title).classes('text-h6 font-bold text-indigo-400 q-mb-sm')
            self.display = ui.label(self.input_data).classes('text-h4 font-mono bg-black/40 w-full text-center q-pa-md rounded border border-gray-700 q-mb-md')
            
            grid = [
                ['7', '8', '9'],
                ['4', '5', '6'],
                ['1', '2', '3'],
                ['.', '0', '⌫']
            ]
            
            with ui.column().classes('w-full gap-2'):
                for row in grid:
                    with ui.row().classes('w-full justify-around gap-2 no-wrap'):
                        for key in row:
                            if key == '⌫':
                                ui.button(key, on_click=self._backspace).props('flat bg-orange-9 text-white text-h5').classes('w-20 h-16')
                            else:
                                ui.button(key, on_click=lambda k=key: self._press(k)).props('flat bg-grey-9 text-white text-h5').classes('w-20 h-16')
                
                with ui.row().classes('w-full justify-between q-mt-md px-2'):
                    ui.button('CLEAR', on_click=self._clear).props('flat color=grey-5')
                    ui.button('CANCEL', on_click=self.close).props('flat color=grey-5')
                    ui.button('OK', on_click=self._submit).props('color=indigo text-white').classes('px-6')

    def _press(self, key):
        self.input_data += key
        self.display.set_text(self.input_data)

    def _backspace(self):
        self.input_data = self.input_data[:-1]
        self.display.set_text(self.input_data or '')

    def _clear(self):
        self.input_data = ''
        self.display.set_text('')

    def _submit(self):
        if self.on_save:
            self.on_save(self.input_data)
        self.close()

class IPAddressInput(ui.input):
    """Input field that opens an IP-address numpad on click (touchscreen-friendly)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on('click', self._open_numpad)
        self.props('readonly cursor-pointer')

    def _open_numpad(self):
        IPNumpadDialog(self._props.get('label') or 'Enter IP Address', initial_value=self.value or '', on_save=self._update_val).open()

    def _update_val(self, new_val):
        self.value = new_val

class ValveToggle(ui.element):
    def __init__(self, port_num, initial_state=False, client=None):
        super().__init__('div')
        self.port_num = port_num
        self.state = initial_state
        self.modbus_client = client
        self._user_action_time = 0.0  # Timestamp of last user toggle
        self._debounce_seconds = 3.0  # Ignore polled updates for this long after a user click
        self.classes('relative inline-flex items-center w-[168px] h-[72px] rounded-full cursor-pointer transition-all duration-300 border-4 border-solid shadow-sm select-none shrink-0')
        self.on('click', self.toggle)
        
        with self:
            self.thumb = ui.element('div').classes('absolute w-[54px] h-[54px] bg-white rounded-full shadow-md transition-all duration-300 z-10')
            self.lbl = ui.label('').classes('absolute text-white font-bold text-lg tracking-wider pointer-events-none transition-all duration-300 z-0')
            
        self._update_appearance()

    def toggle(self):
        import time
        self.state = not self.state
        self._user_action_time = time.time()
        self._update_appearance()
        if self.modbus_client:
            asyncio.create_task(self.modbus_client.write_valve(self.port_num, self.state))

    def update_state(self, new_state: bool):
        import time
        # Ignore polled state updates while the physical valve is still actuating
        if time.time() - self._user_action_time < self._debounce_seconds:
            return
        if self.state != new_state:
            self.state = new_state
            self._update_appearance()

    def _update_appearance(self):
        if self.state:
            self.classes(remove='border-white bg-[#303030]', add='border-[#20c997] bg-[#20c997]')
            self.thumb.classes(remove='left-[8px]', add='left-[102px]')
            self.lbl.set_text('OPEN')
            self.lbl.classes(remove='right-[16px]', add='left-[16px]')
        else:
            self.classes(remove='border-[#20c997] bg-[#20c997]', add='border-white bg-[#303030]')
            self.thumb.classes(remove='left-[102px]', add='left-[8px]')
            self.lbl.set_text('CLOSED')
            self.lbl.classes(remove='left-[16px]', add='right-[16px]')

class SimulationToggle(ui.element):
    def __init__(self, initial_state=False):
        super().__init__('div')
        self.state = initial_state
        self.classes('relative inline-flex items-center w-[168px] h-[72px] rounded-full cursor-pointer transition-all duration-300 border-4 border-solid shadow-sm select-none shrink-0')
        self.on('click', self.toggle)
        
        with self:
            self.thumb = ui.element('div').classes('absolute w-[54px] h-[54px] bg-white rounded-full shadow-md transition-all duration-300 z-10')
            self.lbl = ui.label('').classes('absolute text-white font-bold text-lg tracking-wider pointer-events-none transition-all duration-300 z-0')
            
        self._update_appearance()

    def toggle(self):
        self.state = not self.state
        settings["use_simulation"] = self.state
        save_settings()
        self._update_appearance()

    def _update_appearance(self):
        if self.state:
            self.classes(remove='border-white bg-[#303030]', add='border-[#20c997] bg-[#20c997]')
            self.thumb.classes(remove='left-[8px]', add='left-[102px]')
            self.lbl.set_text('SIM ON')
            self.lbl.classes(remove='right-[16px]', add='left-[16px]')
        else:
            self.classes(remove='border-[#20c997] bg-[#20c997]', add='border-white bg-[#303030]')
            self.thumb.classes(remove='left-[102px]', add='left-[8px]')
            self.lbl.set_text('SIM OFF')
            self.lbl.classes(remove='left-[16px]', add='right-[16px]')

class HostNetworkToggle(ui.element):
    def __init__(self, initial_state=False, on_change=None):
        super().__init__('div')
        self.state = initial_state
        self._on_change = on_change
        self.is_processing = False
        # Make the pill wider to fit longer text
        self.classes('relative inline-flex items-center w-[168px] h-[72px] rounded-full cursor-pointer transition-all duration-300 border-4 border-solid shadow-sm select-none shrink-0')
        self.on('click', self.toggle)
        
        with self:
            self.thumb = ui.element('div').classes('absolute w-[54px] h-[54px] bg-white rounded-full shadow-md transition-all duration-300 z-10')
            self.lbl = ui.label('').classes('absolute text-white font-bold text-lg tracking-wider pointer-events-none transition-all duration-300 z-0')
            
        self._update_appearance()

    async def toggle(self):
        if self.is_processing:
            return
            
        self.state = not self.state
        self._update_appearance()
        if self._on_change:
            import inspect
            if inspect.iscoroutinefunction(self._on_change):
                await self._on_change(self.state)
            else:
                self._on_change(self.state)

    def set_processing(self, is_working: bool):
        self.is_processing = is_working
        if is_working:
            self.classes(add='animate-pulse')
            self.classes(remove='border-[#20c997] bg-[#20c997] border-white bg-[#303030]', add='border-orange-500 bg-orange-500')
            if self.state:
                self.lbl.set_text('STARTING')
            else:
                self.lbl.set_text('STOPPING')
        else:
            self.classes(remove='animate-pulse border-orange-500 bg-orange-500')
            self._update_appearance()

    def _update_appearance(self):
        if self.is_processing:
            return
            
        if self.state:
            self.classes(remove='border-white bg-[#303030] border-orange-500 bg-orange-500', add='border-[#20c997] bg-[#20c997]')
            self.thumb.classes(remove='left-[8px]', add='left-[102px]')
            self.lbl.set_text('HOST ON')
            self.lbl.classes(remove='right-[16px]', add='left-[16px]')
        else:
            self.classes(remove='border-[#20c997] bg-[#20c997] border-orange-500 bg-orange-500', add='border-white bg-[#303030]')
            self.thumb.classes(remove='left-[102px]', add='left-[8px]')
            self.lbl.set_text('HOST OFF')
            self.lbl.classes(remove='left-[16px]', add='right-[16px]')

class GaugeSettingsDialog(ui.dialog):
    def __init__(self, port_num, metric_name, display_label, on_save):
        super().__init__()
        self.port_num = port_num
        self.metric = metric_name
        self.on_save = on_save
        
        # Keys for settings
        max_key = f"{port_num}_{metric_name}_max"
        caution_key = f"{port_num}_{metric_name}_caution"
        warn_key = f"{port_num}_{metric_name}_warn"
        
        # Color Keys
        color_norm_key = f"{port_num}_{metric_name}_color_norm"
        color_caut_key = f"{port_num}_{metric_name}_color_caut"
        color_warn_key = f"{port_num}_{metric_name}_color_warn"
        
        with self, ui.card().classes('w-96 q-pa-md bg-[#1a1c1e] text-white border-2 border-indigo-500 shadow-2xl'):
            ui.label(f"Gauge Settings").classes('text-h6 font-bold text-indigo-400')
            ui.label(display_label).classes('text-subtitle2 text-grey-4 q-mb-md')
            
            with ui.column().classes('w-full gap-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    ui.label("Gauge Max Scale").classes('text-grey-4')
                    max_input = NumberInput(label="Max Scale", value=float(settings.get(max_key, 1000.0))).props('dark outlined dense').classes('w-32')

                ui.separator().classes('bg-gray-700')
                
                with ui.row().classes('w-full items-center gap-4'):
                    with ui.column().classes('flex-grow'):
                         ui.label("Caution Threshold").classes('text-grey-4 text-xs font-bold')
                         caution_input = NumberInput(label="Caution Threshold", value=float(settings.get(caution_key, 600.0))).props('dark outlined dense').classes('w-full')
                    with ui.column().classes('flex-grow'):
                         ui.label("Warning Threshold").classes('text-grey-4 text-xs font-bold')
                         warn_input = NumberInput(label="Warning Threshold", value=float(settings.get(warn_key, 800.0))).props('dark outlined dense').classes('w-full')

                ui.separator().classes('bg-gray-700')
                ui.label("State Colors").classes('text-xs font-bold text-indigo-300 uppercase tracking-widest')
                
                with ui.row().classes('w-full items-center gap-2'):
                    ui.label("Normal").classes('text-xs text-grey-5 w-12')
                    color_norm = ui.color_input(value=settings.get(color_norm_key, '#3b82f6')).props('dark outlined dense').classes('flex-grow')
                    
                with ui.row().classes('w-full items-center gap-2'):
                    ui.label("Caution").classes('text-xs text-grey-5 w-12')
                    color_caut = ui.color_input(value=settings.get(color_caut_key, '#f59e0b')).props('dark outlined dense').classes('flex-grow')

                with ui.row().classes('w-full items-center gap-2'):
                    ui.label("Warning").classes('text-xs text-grey-5 w-12')
                    color_warn = ui.color_input(value=settings.get(color_warn_key, '#ef4444')).props('dark outlined dense').classes('flex-grow')

                with ui.row().classes('w-full justify-end q-mt-md gap-3'):
                    ui.button("Cancel", on_click=self.close).props('flat color=grey')
                    def save():
                        settings[max_key] = max_input.value
                        settings[caution_key] = caution_input.value
                        settings[warn_key] = warn_input.value
                        settings[color_norm_key] = color_norm.value
                        settings[color_caut_key] = color_caut.value
                        settings[color_warn_key] = color_warn.value
                        save_settings()
                        if on_save:
                            on_save()
                        self.close()
                    ui.button("Save Changes", on_click=save).props('color=indigo text-white').classes('px-6')

class StorageBrowserDialog(ui.dialog):
    def __init__(self, initial_dir='/mnt', on_select=None):
        super().__init__()
        self.on_select = on_select
        if not initial_dir or not os.path.exists(initial_dir):
            self.current_dir = os.path.abspath('/')
        else:
            self.current_dir = os.path.abspath(initial_dir)
            
        with self, ui.card().classes('w-[700px] max-w-[95vw] bg-[#1a1c1e] text-white border-2 border-primary shadow-2xl q-pa-md'):
            with ui.row().classes('w-full items-center justify-between q-mb-sm'):
                ui.label("Select Storage Directory").classes('text-h6 font-bold text-primary')
                ui.button(icon='close', on_click=self.close).props('flat round size=sm text-grey')
                
            self.path_lbl = ui.label(self.current_dir).classes('font-mono text-sm bg-black/40 q-pa-sm rounded border border-gray-700 w-full truncate q-mb-md')
            self.list_container = ui.column().classes('w-full h-64 overflow-y-auto bg-black/20 rounded border border-gray-800 q-pa-xs gap-1')
            
            with ui.row().classes('w-full justify-between items-center q-mt-md'):
                ui.button("New Folder", icon="create_new_folder", on_click=self._new_folder).props('flat color=info size=sm')
                ui.button("Select Current Directory", icon="check_circle", on_click=self._confirm).props('color=primary text-white')

            ui.separator().classes('w-full q-my-md bg-gray-700')
            
            with ui.expansion("Format & Mount Hardware SSD", icon="save").classes('w-full bg-black/30 rounded border border-gray-800'):
                ui.label("Discovers available internal block devices. Formatting mounts volume directly to /mnt/ssd.").classes('text-xs text-grey-4 q-mb-sm')
                self.drive_select = ui.select({}, label="Target Hardware Volume").classes('w-full q-mb-sm')
                self.format_btn = ui.button("Format & Mount Drive", color="red", icon="warning", on_click=self._format_drive).classes('w-full').props('dense')
                
            self._refresh()

    def _refresh(self):
        self.path_lbl.set_text(self.current_dir)
        self.list_container.clear()
        
        drives = {}
        try:
            out = subprocess.check_output("lsblk -d -o NAME,SIZE,MODEL,TYPE", shell=True).decode()
            for line in out.split("\n"):
                if not line or "NAME" in line: continue
                parts = line.split()
                if len(parts) >= 3 and "disk" in line:
                    name = parts[0]
                    size = parts[1]
                    model = " ".join(parts[2:-1]) if len(parts) > 3 else parts[2]
                    if name.startswith("nvme") or name.startswith("sd"):
                        drives[name] = f"/dev/{name} - {size} ({model})"
        except Exception:
            pass
            
        self.drive_select.options = drives
        self.drive_select.update()
        if drives and not self.drive_select.value:
            self.drive_select.value = list(drives.keys())[0]

        with self.list_container:
            parent = os.path.dirname(self.current_dir)
            if parent != self.current_dir:
                with ui.row().classes('w-full items-center justify-between q-pa-xs hover:bg-white/10 rounded cursor-pointer no-wrap').on('click', lambda: self._nav(parent)):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('folder_open', size='sm').classes('text-amber')
                        ui.label(".. (Parent Directory)").classes('text-xs font-bold text-grey-3')
            
            try:
                items = sorted(os.listdir(self.current_dir))
                for item in items:
                    full_path = os.path.join(self.current_dir, item)
                    if os.path.isdir(full_path):
                        with ui.row().classes('w-full items-center justify-between q-pa-xs hover:bg-white/10 rounded cursor-pointer no-wrap').on('click', lambda p=full_path: self._nav(p)):
                            with ui.row().classes('items-center gap-2 truncate'):
                                ui.icon('folder', size='sm').classes('text-amber')
                                ui.label(item).classes('text-xs text-white truncate')
            except Exception as e:
                ui.label(f"Access Denied: {e}").classes('text-xs text-red q-pa-sm')

    def _nav(self, path):
        self.current_dir = os.path.abspath(path)
        self._refresh()

    def _confirm(self):
        if self.on_select:
            self.on_select(self.current_dir)
        self.close()

    def _new_folder(self):
        def save_folder(name):
            if not name: return
            target = os.path.join(self.current_dir, name.strip())
            try:
                os.makedirs(target, exist_ok=True)
                ui.notify(f"Created folder {name}", type="positive")
                self._nav(target)
            except Exception as e:
                ui.notify(f"Error creating folder: {e}", type="negative")
                
        KeyboardDialog("New Folder Name", initial_value="", on_save=save_folder).open()

    async def _format_drive(self):
        dev = self.drive_select.value
        if not dev:
            ui.notify("No drive selected", type="warning")
            return
            
        with ui.dialog() as confirm_dlg, ui.card().classes('bg-dark border border-red-500'):
            ui.label(f"WARNING: Formatting /dev/{dev} will PERMANENTLY ERASE all contents!").classes('text-red font-bold')
            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button("Cancel", on_click=confirm_dlg.close).props('flat')
                async def do_format():
                    confirm_dlg.close()
                    self.format_btn.props('loading')
                    ui.notify(f"Formatting /dev/{dev} and mounting to /mnt/ssd...", type="info", timeout=5000)
                    try:
                        proc = await asyncio.create_subprocess_exec("sudo", "bash", "/home/pi/modbus_hmi/scripts/setup_ssd.sh", dev, "--force")
                        await proc.communicate()
                        if proc.returncode == 0:
                            ui.notify("SSD successfully formatted and mounted to /mnt/ssd!", type="positive")
                            self._nav("/mnt/ssd")
                            self._confirm()
                        else:
                            ui.notify("Formatting failed. Verify root privileges or drive state.", type="negative")
                    except Exception as e:
                        ui.notify(f"Execution error: {e}", type="negative")
                    finally:
                        self.format_btn.props(remove='loading')
                ui.button("Erase & Mount", color="red", on_click=do_format)
        confirm_dlg.open()

class StorageLocationInput(ui.input):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on('click', self._open_browser)
        self.props('readonly cursor-pointer outlined')
        
    def _open_browser(self):
        StorageBrowserDialog(initial_dir=self.value or "/mnt", on_select=self._update_val).open()
        
    def _update_val(self, new_dir):
        self.value = new_dir
        self.update()
        # Trigger any bound value change event listener manually if bound to change or blur
        # NiceGUI fires change events when self.value changes via UI interactions
        self._handle_value_change(new_dir)
