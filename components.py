import asyncio
from nicegui import ui
from shared_state import settings, save_settings

class KeyboardDialog(ui.dialog):
    def __init__(self, title, initial_value='', on_save=None):
        super().__init__()
        self.input_data = initial_value
        self.on_save = on_save
        self.caps = False
        
        with self, ui.card().classes('w-[600px] bg-[#1a1c1e] text-white border-2 border-primary shadow-2xl'):
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
        KeyboardDialog(self.label or "Enter Text", initial_value=self.value, on_save=self._update_val).open()
    
    def _update_val(self, new_val):
        self.value = new_val

class NumberInput(ui.number):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.on('click', self._open_numpad)
        self.props('readonly cursor-pointer')

    def _open_numpad(self):
        NumpadDialog(self.label or "Enter Value", initial_value=self.value or 0, on_save=self._update_val).open()

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
        IPNumpadDialog(self.label or 'Enter IP Address', initial_value=self.value or '', on_save=self._update_val).open()

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
