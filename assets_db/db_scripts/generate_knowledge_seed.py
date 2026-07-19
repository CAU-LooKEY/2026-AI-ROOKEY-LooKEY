import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "db_scripts" / "008_seed_knowledge_qa.sql"
TODAY = "2026-07-14"

sources = [
    {"source_key": "arduino_uno_rev3_doc", "title": "UNO R3 Arduino Documentation", "publisher": "Arduino", "source_type": "official_doc", "url": "https://docs.arduino.cc/hardware/uno-rev3", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.98, "notes": "Official board overview, pin counts, processor, and downloadable resources."},
    {"source_key": "arduino_uno_rev3_store_specs", "title": "Arduino UNO Rev3 Store Tech Specs", "publisher": "Arduino", "source_type": "official_doc", "url": "https://store.arduino.cc/products/arduino-uno-rev3", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.97, "notes": "Official product tech specs used for voltage and current limits."},
    {"source_key": "arduino_nano_doc", "title": "Nano Arduino Documentation", "publisher": "Arduino", "source_type": "official_doc", "url": "https://docs.arduino.cc/hardware/nano", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.98, "notes": "Official Nano hardware page and downloadable resources."},
    {"source_key": "arduino_nano_datasheet_a000005", "title": "Arduino Nano A000005 Datasheet", "publisher": "Arduino", "source_type": "datasheet", "url": "https://docs.arduino.cc/resources/datasheets/A000005-datasheet.pdf", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.98, "notes": "Official classic Nano datasheet."},
    {"source_key": "arduino_nano_pinout_pdf", "title": "Arduino Nano Pinout PDF", "publisher": "Arduino", "source_type": "official_doc", "url": "https://content.arduino.cc/assets/Pinout-NANO_latest.pdf", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.97, "notes": "Official pinout PDF; includes VIN, current limits, and pin functions."},
    {"source_key": "arduino_blink_example", "title": "Blink Arduino Built-in Example", "publisher": "Arduino", "source_type": "official_example", "url": "https://www.arduino.cc/en/Tutorial/Blink", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.96, "notes": "Official LED blink example; used as source for beginner LED task patterns."},
    {"source_key": "arduino_input_pullup_example", "title": "InputPullupSerial Arduino Built-in Example", "publisher": "Arduino", "source_type": "official_example", "url": "https://docs.arduino.cc/built-in-examples/digital/InputPullupSerial/", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.96, "notes": "Official INPUT_PULLUP example for switches/buttons."},
    {"source_key": "arduino_servo_reference", "title": "Arduino Servo Library Reference", "publisher": "Arduino", "source_type": "official_doc", "url": "https://www.arduino.cc/reference/en/libraries/servo/", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.96, "notes": "Official Servo library reference and examples."},
    {"source_key": "hcsr04_elecfreaks_datasheet", "title": "HC-SR04 Ultrasonic Ranging Module Datasheet", "publisher": "ElecFreaks via SparkFun CDN", "source_type": "datasheet", "url": "https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.92, "notes": "Datasheet used for voltage, current, timing, frequency, and range."},
    {"source_key": "adafruit_ultrasonic_guide", "title": "Ultrasonic Sonar Distance Sensors Guide", "publisher": "Adafruit", "source_type": "vendor_guide", "url": "https://cdn-learn.adafruit.com/downloads/pdf/ultrasonic-sonar-distance-sensors.pdf", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.90, "notes": "Used for 3.3V microcontroller/Raspberry Pi HC-SR04 voltage-divider caution."},
    {"source_key": "sg90_luxorparts_datasheet", "title": "SG90 Micro Servo Datasheet", "publisher": "Luxorparts / Kjell", "source_type": "datasheet", "url": "https://www.kjell.com/globalassets/mediaassets/701916_87897_datasheet_en.pdf", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.90, "notes": "Representative SG90 datasheet with voltage, current, PWM, and wire colors."},
    {"source_key": "vishay_tlhb5400_blue_led_datasheet", "title": "Vishay TLHB5400 Blue 5mm LED Datasheet", "publisher": "Vishay via Farnell", "source_type": "datasheet", "url": "https://www.farnell.com/datasheets/2050817.pdf", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.88, "notes": "Representative 5mm blue LED electrical data; asset is generic, so values require final part review."},
    {"source_key": "digikey_resistor_color_code_calculator", "title": "DigiKey Resistor Color Code Calculator", "publisher": "DigiKey", "source_type": "calculator", "url": "https://www.digikey.com/en/resources/conversion-calculators/conversion-calculator-resistor-color-code", "retrieved_at": TODAY, "license_status": "needs_review", "reliability_score": 0.90, "notes": "Reference for color-banded axial resistor identification."},
    {"source_key": "local_breadboard_layout_calibration", "title": "Local Breadboard Layout Calibration", "publisher": "CAU-LooKEY assets_db", "source_type": "local_calibration", "url": "https://github.com/CAU-LooKEY/2026-AI-ROOKEY-LooKEY/tree/dev/assets_db/assets_db/db_scripts/breadboard_layouts", "retrieved_at": TODAY, "license_status": "approved", "reliability_score": 0.75, "notes": "Procedural breadboard layout created from uploaded images and local calibration metadata."},
]

specs = [
    {"slug": "arduino-uno-r3", "spec_key": "logic_and_power_limits", "spec_category": "power", "summary": "Uno R3 uses 5V logic, supports 7-12V recommended external input, and should keep GPIO current within board limits.", "spec_value": {"logic_voltage_v": 5, "vin_recommended_v": [7, 12], "vin_limit_v": [6, 20], "dc_current_per_io_pin_ma": 20, "dc_current_3v3_pin_ma": 50}, "source_keys": ["arduino_uno_rev3_doc", "arduino_uno_rev3_store_specs"], "confidence_score": 0.96, "review_status": "reviewed"},
    {"slug": "arduino-uno-r3", "spec_key": "io_capabilities", "spec_category": "io", "summary": "Uno R3 exposes 14 digital I/O pins, 6 PWM-capable pins, and 6 analog inputs.", "spec_value": {"digital_io_pins": 14, "pwm_pins": 6, "analog_input_pins": 6, "interfaces": ["UART", "I2C", "SPI"], "clock_mhz": 16}, "source_keys": ["arduino_uno_rev3_doc"], "confidence_score": 0.97, "review_status": "reviewed"},
    {"slug": "arduino-nano", "spec_key": "logic_and_power_limits", "spec_category": "power", "summary": "Classic Nano uses 5V logic, VIN is documented as 7-12V, and the pinout limits I/O current to 20mA.", "spec_value": {"logic_voltage_v": 5, "vin_recommended_v": [7, 12], "dc_current_per_io_pin_ma": 20, "dc_current_3v3_pin_ma": 50}, "source_keys": ["arduino_nano_doc", "arduino_nano_pinout_pdf"], "confidence_score": 0.95, "review_status": "reviewed"},
    {"slug": "arduino-nano", "spec_key": "io_capabilities", "spec_category": "io", "summary": "Classic Nano provides breadboard-friendly headers with 14 named digital pins and 8 analog inputs; A6/A7 are analog-only in common Nano pinouts.", "spec_value": {"named_digital_io_pins": 14, "total_digital_io_pins_from_datasheet": 20, "pwm_pins": 6, "analog_input_pins": 8, "interfaces": ["UART", "I2C", "SPI"], "clock_mhz": 16}, "source_keys": ["arduino_nano_datasheet_a000005", "arduino_nano_pinout_pdf"], "confidence_score": 0.94, "review_status": "reviewed"},
    {"slug": "hc-sr04", "spec_key": "electrical_and_timing", "spec_category": "timing", "summary": "HC-SR04 is a 5V ultrasonic module that starts measurement from a 10us trigger pulse and reports distance through echo pulse width.", "spec_value": {"working_voltage_v": 5, "working_current_ma_typical": 15, "ultrasonic_frequency_khz": 40, "trigger_pulse_us_min": 10, "echo_signal": "TTL pulse width proportional to distance"}, "source_keys": ["hcsr04_elecfreaks_datasheet"], "confidence_score": 0.93, "review_status": "reviewed"},
    {"slug": "hc-sr04", "spec_key": "measurement_range", "spec_category": "measurement", "summary": "Representative HC-SR04 range is 2cm to 400cm with about 3mm nominal accuracy under datasheet conditions.", "spec_value": {"min_range_cm": 2, "max_range_cm": 400, "accuracy_mm": 3, "measuring_angle_deg": 15}, "source_keys": ["hcsr04_elecfreaks_datasheet"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"slug": "hc-sr04", "spec_key": "logic_level_caution", "spec_category": "safety", "summary": "When HC-SR04 is used with 3.3V GPIO boards, its 5V echo signal needs level shifting or a voltage divider.", "spec_value": {"echo_logic_v": 5, "requires_level_shift_for_3v3_gpio": True, "recommended_method": "voltage divider or level shifter"}, "source_keys": ["adafruit_ultrasonic_guide"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"slug": "servo-sg90", "spec_key": "power_and_pwm", "spec_category": "interface", "summary": "SG90 servos are powered from about 4.8-6V and use 50Hz PWM with roughly 1-2ms pulses across the 0-180 degree range.", "spec_value": {"operating_voltage_v": [4.8, 6.0], "current_ma_max_less_than": 600, "pwm_frequency_hz": 50, "pwm_period_ms": 20, "pulse_width_us": {"min": 1000, "center": 1500, "max": 2000}, "rotation_degrees": 180}, "source_keys": ["sg90_luxorparts_datasheet", "arduino_servo_reference"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"slug": "servo-sg90", "spec_key": "wire_colors", "spec_category": "interface", "summary": "Representative SG90 cable colors are brown for ground, red for supply, and orange for PWM signal.", "spec_value": {"brown": "GND", "red": "VCC", "orange": "SIGNAL"}, "source_keys": ["sg90_luxorparts_datasheet"], "confidence_score": 0.88, "review_status": "reviewed"},
    {"slug": "led-5mm-blue", "spec_key": "representative_blue_led_limits", "spec_category": "power", "summary": "Representative 5mm blue LED data: 20mA DC forward current and around 3.9V typical forward voltage; exact values depend on final LED part.", "spec_value": {"dc_forward_current_ma": 20, "forward_voltage_v_typical": 3.9, "forward_voltage_v_max": 4.5, "reverse_voltage_v": 5, "dominant_wavelength_nm_typical": 466}, "source_keys": ["vishay_tlhb5400_blue_led_datasheet"], "confidence_score": 0.78, "review_status": "needs_review"},
    {"slug": "led-5mm-blue", "spec_key": "polarity", "spec_category": "behavior", "summary": "LEDs are polarized components: anode and cathode orientation matters for current flow.", "spec_value": {"polarized": True, "positive_terminal": "ANODE", "negative_terminal": "CATHODE"}, "source_keys": ["vishay_tlhb5400_blue_led_datasheet", "arduino_blink_example"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"slug": "resistor-220-ohm", "spec_key": "resistance_and_color_code", "spec_category": "passive", "summary": "220 ohm through-hole resistor represented as a non-polarized two-lead part; common 4-band code is red-red-brown with gold tolerance.", "spec_value": {"resistance_ohm": 220, "tolerance_percent_assumed": 5, "color_bands_4_band": ["red", "red", "brown", "gold"], "polarized": False}, "source_keys": ["digikey_resistor_color_code_calculator"], "confidence_score": 0.86, "review_status": "needs_review"},
    {"slug": "pushbutton-6x6", "spec_key": "momentary_switch_behavior", "spec_category": "behavior", "summary": "A tactile pushbutton is treated as a momentary non-polarized switch; with INPUT_PULLUP and one side to GND, pressed reads LOW.", "spec_value": {"momentary": True, "polarized": False, "recommended_input_mode": "INPUT_PULLUP", "pressed_state_when_to_ground": "LOW", "released_state": "HIGH"}, "source_keys": ["arduino_input_pullup_example"], "confidence_score": 0.88, "review_status": "reviewed"},
    {"slug": "breadboard-half", "spec_key": "procedural_layout_role", "spec_category": "passive", "summary": "Half-size breadboard is a passive prototyping interconnect; full hole coordinates are generated from procedural layout metadata.", "spec_value": {"active_component": False, "coordinate_source": "circuit_breadboard_layouts", "rails": "top and bottom power rails", "terminal_rows": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]}, "source_keys": ["local_breadboard_layout_calibration"], "confidence_score": 0.80, "review_status": "needs_review"},
    {"slug": "breadboard-full", "spec_key": "procedural_layout_role", "spec_category": "passive", "summary": "Full-size breadboard is a passive prototyping interconnect; split rails and hole coordinates are generated from procedural layout metadata.", "spec_value": {"active_component": False, "coordinate_source": "circuit_breadboard_layouts", "rails": "split top and bottom power rails", "terminal_rows": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]}, "source_keys": ["local_breadboard_layout_calibration"], "confidence_score": 0.80, "review_status": "needs_review"},
]

snippets = [
    {"snippet_key": "arduino_led_blink_d9", "title": "Blink an external LED on D9", "platform": "arduino", "language": "cpp", "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["led-5mm-blue", "resistor-220-ohm"], "code": "const int LED_PIN = 9;\\n\\nvoid setup() {\\n  pinMode(LED_PIN, OUTPUT);\\n}\\n\\nvoid loop() {\\n  digitalWrite(LED_PIN, HIGH);\\n  delay(1000);\\n  digitalWrite(LED_PIN, LOW);\\n  delay(1000);\\n}\\n", "setup_notes": ["Use a current-limiting resistor in series with the LED.", "Match LED polarity: anode toward the output side and cathode toward GND."], "source_keys": ["arduino_blink_example"], "confidence_score": 0.94, "review_status": "reviewed"},
    {"snippet_key": "arduino_button_input_pullup_d2", "title": "Read a pushbutton with INPUT_PULLUP on D2", "platform": "arduino", "language": "cpp", "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["pushbutton-6x6"], "code": "const int BUTTON_PIN = 2;\\n\\nvoid setup() {\\n  Serial.begin(9600);\\n  pinMode(BUTTON_PIN, INPUT_PULLUP);\\n}\\n\\nvoid loop() {\\n  int pressed = digitalRead(BUTTON_PIN) == LOW;\\n  Serial.println(pressed ? \"pressed\" : \"released\");\\n  delay(50);\\n}\\n", "setup_notes": ["With INPUT_PULLUP, connect the button between the input pin and GND.", "Pressed reads LOW and released reads HIGH."], "source_keys": ["arduino_input_pullup_example"], "confidence_score": 0.94, "review_status": "reviewed"},
    {"snippet_key": "arduino_hcsr04_distance_trig9_echo10", "title": "Measure distance with HC-SR04", "platform": "arduino", "language": "cpp", "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["hc-sr04"], "code": "const int TRIG_PIN = 9;\\nconst int ECHO_PIN = 10;\\n\\nvoid setup() {\\n  Serial.begin(9600);\\n  pinMode(TRIG_PIN, OUTPUT);\\n  pinMode(ECHO_PIN, INPUT);\\n}\\n\\nvoid loop() {\\n  digitalWrite(TRIG_PIN, LOW);\\n  delayMicroseconds(2);\\n  digitalWrite(TRIG_PIN, HIGH);\\n  delayMicroseconds(10);\\n  digitalWrite(TRIG_PIN, LOW);\\n\\n  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);\\n  float distanceCm = duration / 58.0;\\n  Serial.println(distanceCm);\\n  delay(100);\\n}\\n", "setup_notes": ["HC-SR04 VCC is commonly 5V on Arduino Uno/Nano.", "For 3.3V GPIO boards, level-shift the Echo signal."], "source_keys": ["hcsr04_elecfreaks_datasheet", "adafruit_ultrasonic_guide"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"snippet_key": "arduino_servo_sg90_sweep_d9", "title": "Sweep an SG90 servo on D9", "platform": "arduino", "language": "cpp", "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["servo-sg90"], "code": "#include <Servo.h>\\n\\nServo servo;\\nconst int SERVO_PIN = 9;\\n\\nvoid setup() {\\n  servo.attach(SERVO_PIN);\\n}\\n\\nvoid loop() {\\n  for (int angle = 0; angle <= 180; angle++) {\\n    servo.write(angle);\\n    delay(15);\\n  }\\n  for (int angle = 180; angle >= 0; angle--) {\\n    servo.write(angle);\\n    delay(15);\\n  }\\n}\\n", "setup_notes": ["Use a stable 5V supply for the servo when load current is high.", "Connect servo GND and board GND together."], "source_keys": ["arduino_servo_reference", "sg90_luxorparts_datasheet"], "confidence_score": 0.90, "review_status": "reviewed"},
]

issues = [
    {"issue_key": "led_does_not_light", "title": "LED does not light", "severity": "warning", "symptom_patterns": ["LED stays off", "LED does not blink", "blink code uploads but no light"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["led-5mm-blue", "resistor-220-ohm"], "likely_causes": ["LED polarity reversed", "No current-limiting resistor or resistor not in series", "Code pin number does not match physical pin", "GND path missing"], "diagnostic_steps": ["Check that the LED cathode side ultimately reaches GND.", "Confirm the resistor is in series, not in a disconnected breadboard row.", "Compare the code constant with the selected board pin."], "fixes": ["Flip LED orientation if anode/cathode are reversed.", "Move resistor and LED leads into connected breadboard rows.", "Update code or circuit to use the same pin."], "source_keys": ["arduino_blink_example", "vishay_tlhb5400_blue_led_datasheet"], "confidence_score": 0.88, "review_status": "reviewed"},
    {"issue_key": "button_reads_randomly", "title": "Button input reads randomly", "severity": "warning", "symptom_patterns": ["button value flickers", "button reads pressed without touching", "serial monitor alternates randomly"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["pushbutton-6x6"], "likely_causes": ["Input pin is floating", "Button is rotated into the wrong breadboard rows", "INPUT_PULLUP logic is interpreted backwards"], "diagnostic_steps": ["Verify pinMode uses INPUT_PULLUP or add an external pull resistor.", "Check that one button side goes to the input pin and the opposite side goes to GND.", "Remember pressed is LOW with INPUT_PULLUP."], "fixes": ["Use INPUT_PULLUP and wire the button to GND.", "Rotate or move the button so the two switch terminals are on separate breadboard rows.", "Invert the pressed/released logic in code if needed."], "source_keys": ["arduino_input_pullup_example"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"issue_key": "hcsr04_no_echo_or_zero_distance", "title": "HC-SR04 reports zero or no echo", "severity": "warning", "symptom_patterns": ["distance is zero", "pulseIn times out", "HC-SR04 returns no echo"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["hc-sr04"], "likely_causes": ["Missing common ground", "Trigger pulse is shorter than 10us", "Trig and Echo pins swapped", "Target is out of measurable range"], "diagnostic_steps": ["Confirm VCC, GND, TRIG, and ECHO match the sensor labels.", "Check the trigger pulse is held HIGH for at least 10us.", "Test with a flat object within the 2cm-400cm nominal range."], "fixes": ["Reconnect common GND between board and sensor.", "Use a known-good timing sketch.", "Move object into range and avoid soft/angled reflective targets."], "source_keys": ["hcsr04_elecfreaks_datasheet"], "confidence_score": 0.88, "review_status": "reviewed"},
    {"issue_key": "hcsr04_unsafe_on_3v3_gpio", "title": "HC-SR04 echo is unsafe for 3.3V GPIO", "severity": "risk", "symptom_patterns": ["using HC-SR04 with Raspberry Pi", "using HC-SR04 with 3.3V board", "5V echo into 3.3V GPIO"], "board_slugs": [], "component_slugs": ["hc-sr04"], "likely_causes": ["HC-SR04 Echo can output 5V logic while many GPIO inputs are 3.3V only"], "diagnostic_steps": ["Identify the board GPIO voltage before connecting Echo.", "Check whether a voltage divider or level shifter is present."], "fixes": ["Add a voltage divider or logic level shifter on Echo for 3.3V GPIO boards.", "Use a 3.3V-compatible ultrasonic sensor mode/module when available."], "source_keys": ["adafruit_ultrasonic_guide"], "confidence_score": 0.88, "review_status": "reviewed"},
    {"issue_key": "servo_jitter_or_board_resets", "title": "Servo jitters or resets the board", "severity": "warning", "symptom_patterns": ["servo jitters", "Arduino resets when servo moves", "servo moves erratically"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["servo-sg90"], "likely_causes": ["Servo current draw sags the board supply", "Servo GND is not common with board GND", "PWM signal pin or pulse range is wrong"], "diagnostic_steps": ["Check that servo power is within 4.8-6V.", "Confirm board GND and servo power GND are connected.", "Confirm signal wire is attached to the pin used in code."], "fixes": ["Use an external 5V supply sized for servo current.", "Tie external supply GND to Arduino GND.", "Use Servo library attach pin that matches the circuit."], "source_keys": ["sg90_luxorparts_datasheet", "arduino_servo_reference"], "confidence_score": 0.86, "review_status": "reviewed"},
    {"issue_key": "wrong_resistor_value_for_led", "title": "LED resistor value is uncertain", "severity": "info", "symptom_patterns": ["not sure resistor is 220 ohm", "resistor color bands unclear", "LED too dim or too bright"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["resistor-220-ohm", "led-5mm-blue"], "likely_causes": ["Color bands are read from the wrong end", "Tolerance band is mistaken for a digit band", "Actual LED forward voltage differs from representative value"], "diagnostic_steps": ["Read the tolerance band last when interpreting color code.", "Measure the resistor with a multimeter if available.", "Estimate LED current from supply voltage, LED forward voltage, and resistance."], "fixes": ["Use the confirmed 220 ohm resistor for beginner Arduino LED circuits.", "Choose a larger resistor if the LED current should be reduced."], "source_keys": ["digikey_resistor_color_code_calculator", "vishay_tlhb5400_blue_led_datasheet"], "confidence_score": 0.82, "review_status": "needs_review"},
]

tasks = [
    {"task_key": "arduino_led_blink_external", "title": "Blink an external LED with Arduino", "task_type": "build", "difficulty": "beginner", "user_intent_patterns": ["아두이노 LED 깜빡이기", "blink an LED with Arduino", "LED를 1초마다 켜고 끄기"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["led-5mm-blue", "resistor-220-ohm", "breadboard-half"], "task_payload": {"goal": "Create a beginner LED blink circuit using a current-limited LED path.", "excluded_from_db": "generic connection rules are handled by backend Python"}, "result_payload": {"expected_artifacts": ["2D/3D circuit placement", "Arduino sketch", "safety notes"], "recommended_snippet": "arduino_led_blink_d9"}, "expected_result": "The external LED turns on for one second and off for one second repeatedly.", "code_snippet_key": "arduino_led_blink_d9", "troubleshooting_keys": ["led_does_not_light", "wrong_resistor_value_for_led"], "source_keys": ["arduino_blink_example"], "tags": ["led", "digital_output", "beginner"], "confidence_score": 0.92, "review_status": "reviewed"},
    {"task_key": "arduino_button_input_pullup", "title": "Read a pushbutton with Arduino INPUT_PULLUP", "task_type": "build", "difficulty": "beginner", "user_intent_patterns": ["아두이노 푸쉬버튼 입력", "button with INPUT_PULLUP", "버튼 누르면 시리얼 출력"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["pushbutton-6x6", "breadboard-half"], "task_payload": {"goal": "Read a momentary pushbutton as a digital input using the internal pull-up resistor."}, "result_payload": {"expected_artifacts": ["circuit placement", "Arduino sketch", "pressed LOW explanation"], "recommended_snippet": "arduino_button_input_pullup_d2"}, "expected_result": "The serial monitor reports pressed when the button connects the input to ground.", "code_snippet_key": "arduino_button_input_pullup_d2", "troubleshooting_keys": ["button_reads_randomly"], "source_keys": ["arduino_input_pullup_example"], "tags": ["button", "digital_input", "pullup"], "confidence_score": 0.92, "review_status": "reviewed"},
    {"task_key": "arduino_hcsr04_distance_measure", "title": "Measure distance with HC-SR04 and Arduino", "task_type": "measure", "difficulty": "intermediate", "user_intent_patterns": ["초음파센서 거리 측정", "HC-SR04 distance Arduino", "아두이노 거리 센서 회로"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["hc-sr04"], "task_payload": {"goal": "Trigger the HC-SR04 and compute distance from echo pulse width."}, "result_payload": {"expected_artifacts": ["sensor placement", "Arduino sketch", "timing explanation"], "recommended_snippet": "arduino_hcsr04_distance_trig9_echo10"}, "expected_result": "The serial monitor prints approximate distance in centimeters for objects in range.", "code_snippet_key": "arduino_hcsr04_distance_trig9_echo10", "troubleshooting_keys": ["hcsr04_no_echo_or_zero_distance", "hcsr04_unsafe_on_3v3_gpio"], "source_keys": ["hcsr04_elecfreaks_datasheet", "adafruit_ultrasonic_guide"], "tags": ["ultrasonic", "distance", "sensor"], "confidence_score": 0.90, "review_status": "reviewed"},
    {"task_key": "arduino_sg90_servo_sweep", "title": "Sweep an SG90 servo with Arduino", "task_type": "control", "difficulty": "intermediate", "user_intent_patterns": ["서보모터 0도 180도 움직이기", "SG90 servo sweep Arduino", "아두이노 서보모터 제어"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["servo-sg90"], "task_payload": {"goal": "Control a positional SG90 servo using the Arduino Servo library."}, "result_payload": {"expected_artifacts": ["servo placement", "Arduino sketch", "power caution"], "recommended_snippet": "arduino_servo_sg90_sweep_d9"}, "expected_result": "The servo horn sweeps gradually from 0 to 180 degrees and back.", "code_snippet_key": "arduino_servo_sg90_sweep_d9", "troubleshooting_keys": ["servo_jitter_or_board_resets"], "source_keys": ["arduino_servo_reference", "sg90_luxorparts_datasheet"], "tags": ["servo", "pwm", "actuator"], "confidence_score": 0.88, "review_status": "reviewed"},
    {"task_key": "explain_led_current_limiting", "title": "Explain why an LED needs a resistor", "task_type": "explain", "difficulty": "beginner", "user_intent_patterns": ["LED에 저항이 왜 필요해", "why does LED need resistor", "220옴 저항 역할 설명"], "board_slugs": ["arduino-uno-r3", "arduino-nano"], "component_slugs": ["led-5mm-blue", "resistor-220-ohm"], "task_payload": {"goal": "Explain current limiting for beginner LED circuits using the stored LED and resistor specs."}, "result_payload": {"expected_artifacts": ["plain-language explanation", "Ohm-law estimate", "safety note"], "uses_specs": ["representative_blue_led_limits", "resistance_and_color_code"]}, "expected_result": "The answer explains that the resistor limits LED current and protects both LED and I/O pin.", "code_snippet_key": None, "troubleshooting_keys": ["wrong_resistor_value_for_led", "led_does_not_light"], "source_keys": ["arduino_blink_example", "vishay_tlhb5400_blue_led_datasheet", "digikey_resistor_color_code_calculator"], "tags": ["explanation", "led", "resistor", "safety"], "confidence_score": 0.86, "review_status": "needs_review"},
]


def dumps(rows):
    return json.dumps(rows, ensure_ascii=False, indent=2)


def array_expr(column):
    return f"array(select jsonb_array_elements_text(coalesce({column}, '[]'::jsonb)))"


sql = f"""-- Seed hardware knowledge, Task-Result QA templates, code snippets, and troubleshooting guides.
-- Generic connection-rule data is intentionally excluded; connection rules are handled by the backend Python pipeline.

with source_rows as (
  select * from jsonb_to_recordset($sources${dumps(sources)}$sources$::jsonb) as x(
    source_key text, title text, publisher text, source_type text, url text,
    retrieved_at date, license_status text, reliability_score numeric, notes text
  )
)
insert into public.circuit_knowledge_sources (
  source_key, title, publisher, source_type, url, retrieved_at, license_status, reliability_score, notes
)
select source_key, title, publisher, source_type, url, retrieved_at, license_status, reliability_score, notes
from source_rows
on conflict (source_key) do update
set title = excluded.title,
    publisher = excluded.publisher,
    source_type = excluded.source_type,
    url = excluded.url,
    retrieved_at = excluded.retrieved_at,
    license_status = excluded.license_status,
    reliability_score = excluded.reliability_score,
    notes = excluded.notes,
    updated_at = now();

with spec_rows as (
  select * from jsonb_to_recordset($specs${dumps(specs)}$specs$::jsonb) as x(
    slug text, spec_key text, spec_category text, summary text, spec_value jsonb,
    source_keys jsonb, confidence_score numeric, review_status text, status text
  )
)
insert into public.circuit_component_electrical_specs (
  component_id, spec_key, spec_category, summary, spec_value, source_keys,
  confidence_score, review_status, status
)
select assets.id, spec_rows.spec_key, spec_rows.spec_category, spec_rows.summary,
  spec_rows.spec_value, {array_expr('spec_rows.source_keys')},
  spec_rows.confidence_score, spec_rows.review_status, coalesce(spec_rows.status, 'ready')
from spec_rows
join public.circuit_component_assets assets on assets.slug = spec_rows.slug
on conflict (component_id, spec_key) do update
set spec_category = excluded.spec_category,
    summary = excluded.summary,
    spec_value = excluded.spec_value,
    source_keys = excluded.source_keys,
    confidence_score = excluded.confidence_score,
    review_status = excluded.review_status,
    status = excluded.status,
    updated_at = now();

with snippet_rows as (
  select * from jsonb_to_recordset($snippets${dumps(snippets)}$snippets$::jsonb) as x(
    snippet_key text, title text, platform text, language text, board_slugs jsonb,
    component_slugs jsonb, code text, setup_notes jsonb, source_keys jsonb,
    confidence_score numeric, review_status text, status text
  )
)
insert into public.circuit_code_snippets (
  snippet_key, title, platform, language, board_slugs, component_slugs, code,
  setup_notes, source_keys, confidence_score, review_status, status
)
select snippet_key, title, platform, language,
  {array_expr('board_slugs')}, {array_expr('component_slugs')}, code,
  {array_expr('setup_notes')}, {array_expr('source_keys')},
  confidence_score, review_status, coalesce(status, 'ready')
from snippet_rows
on conflict (snippet_key) do update
set title = excluded.title,
    platform = excluded.platform,
    language = excluded.language,
    board_slugs = excluded.board_slugs,
    component_slugs = excluded.component_slugs,
    code = excluded.code,
    setup_notes = excluded.setup_notes,
    source_keys = excluded.source_keys,
    confidence_score = excluded.confidence_score,
    review_status = excluded.review_status,
    status = excluded.status,
    updated_at = now();

with issue_rows as (
  select * from jsonb_to_recordset($issues${dumps(issues)}$issues$::jsonb) as x(
    issue_key text, title text, severity text, symptom_patterns jsonb, board_slugs jsonb,
    component_slugs jsonb, likely_causes jsonb, diagnostic_steps jsonb, fixes jsonb,
    source_keys jsonb, confidence_score numeric, review_status text, status text
  )
)
insert into public.circuit_troubleshooting_guides (
  issue_key, title, severity, symptom_patterns, board_slugs, component_slugs,
  likely_causes, diagnostic_steps, fixes, source_keys, confidence_score, review_status, status
)
select issue_key, title, severity,
  {array_expr('symptom_patterns')}, {array_expr('board_slugs')}, {array_expr('component_slugs')},
  likely_causes, diagnostic_steps, fixes, {array_expr('source_keys')},
  confidence_score, review_status, coalesce(status, 'ready')
from issue_rows
on conflict (issue_key) do update
set title = excluded.title,
    severity = excluded.severity,
    symptom_patterns = excluded.symptom_patterns,
    board_slugs = excluded.board_slugs,
    component_slugs = excluded.component_slugs,
    likely_causes = excluded.likely_causes,
    diagnostic_steps = excluded.diagnostic_steps,
    fixes = excluded.fixes,
    source_keys = excluded.source_keys,
    confidence_score = excluded.confidence_score,
    review_status = excluded.review_status,
    status = excluded.status,
    updated_at = now();

with task_rows as (
  select * from jsonb_to_recordset($tasks${dumps(tasks)}$tasks$::jsonb) as x(
    task_key text, title text, task_type text, difficulty text, user_intent_patterns jsonb,
    board_slugs jsonb, component_slugs jsonb, task_payload jsonb, result_payload jsonb,
    expected_result text, code_snippet_key text, troubleshooting_keys jsonb, source_keys jsonb,
    tags jsonb, confidence_score numeric, review_status text, status text
  )
)
insert into public.circuit_task_result_templates (
  task_key, title, task_type, difficulty, user_intent_patterns, board_slugs, component_slugs,
  task_payload, result_payload, expected_result, code_snippet_key, troubleshooting_keys,
  source_keys, tags, confidence_score, review_status, status
)
select task_key, title, task_type, difficulty,
  {array_expr('user_intent_patterns')}, {array_expr('board_slugs')}, {array_expr('component_slugs')},
  task_payload, result_payload, expected_result, code_snippet_key,
  {array_expr('troubleshooting_keys')}, {array_expr('source_keys')}, {array_expr('tags')},
  confidence_score, review_status, coalesce(status, 'ready')
from task_rows
on conflict (task_key) do update
set title = excluded.title,
    task_type = excluded.task_type,
    difficulty = excluded.difficulty,
    user_intent_patterns = excluded.user_intent_patterns,
    board_slugs = excluded.board_slugs,
    component_slugs = excluded.component_slugs,
    task_payload = excluded.task_payload,
    result_payload = excluded.result_payload,
    expected_result = excluded.expected_result,
    code_snippet_key = excluded.code_snippet_key,
    troubleshooting_keys = excluded.troubleshooting_keys,
    source_keys = excluded.source_keys,
    tags = excluded.tags,
    confidence_score = excluded.confidence_score,
    review_status = excluded.review_status,
    status = excluded.status,
    updated_at = now();
"""

OUT.write_text(sql, encoding="utf-8")
print(f"Wrote {OUT}")
print(f"{len(sources)} sources, {len(specs)} specs, {len(snippets)} snippets, {len(tasks)} tasks, {len(issues)} issues")
