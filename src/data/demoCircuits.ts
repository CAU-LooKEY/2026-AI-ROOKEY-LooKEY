import type { CircuitScene } from "../types/circuit";

export const demoCircuits: CircuitScene[] = [
  {
    id: "uno-led",
    title: "Uno + LED",
    prompt: "Arduino Uno D13 pin to 220 ohm resistor, red LED, and GND",
    placements: [
      { id: "uno", componentSlug: "arduino-uno-r3", gridX: 3, gridY: 4 },
      { id: "resistor", componentSlug: "resistor-220ohm", gridX: 11, gridY: 3 },
      { id: "led", componentSlug: "led-5mm-red", gridX: 15, gridY: 2 },
    ],
    connections: [
      { id: "uno-d13-resistor", from: { placementId: "uno", pinKey: "D13" }, to: { placementId: "resistor", pinKey: "A" }, color: "#f59e0b", label: "D13" },
      { id: "resistor-led", from: { placementId: "resistor", pinKey: "B" }, to: { placementId: "led", pinKey: "ANODE" }, color: "#ef4444", label: "+" },
      { id: "led-ground", from: { placementId: "led", pinKey: "CATHODE" }, to: { placementId: "uno", pinKey: "GND_D" }, color: "#334155", label: "GND" },
    ],
  },
  {
    id: "nano-dht11",
    title: "Nano + DHT11",
    prompt: "Arduino Nano D2 reads DHT11 data with 5V and GND",
    placements: [
      { id: "nano", componentSlug: "arduino-nano", gridX: 4, gridY: 5 },
      { id: "dht", componentSlug: "dht11", gridX: 13, gridY: 3 },
    ],
    connections: [
      { id: "nano-d2-dht-data", from: { placementId: "nano", pinKey: "D2" }, to: { placementId: "dht", pinKey: "DATA" }, color: "#14b8a6", label: "DATA" },
      { id: "nano-5v-dht-vcc", from: { placementId: "nano", pinKey: "5V" }, to: { placementId: "dht", pinKey: "VCC" }, color: "#ef4444", label: "5V" },
      { id: "nano-gnd-dht-gnd", from: { placementId: "nano", pinKey: "GND_1" }, to: { placementId: "dht", pinKey: "GND" }, color: "#334155", label: "GND" },
    ],
  },
  {
    id: "pi-led",
    title: "Raspberry Pi + LED",
    prompt: "Raspberry Pi GPIO17 to resistor, red LED, and physical pin 6 GND",
    placements: [
      { id: "pi", componentSlug: "raspberry-pi-4b", gridX: 3, gridY: 4 },
      { id: "resistor", componentSlug: "resistor-220ohm", gridX: 12, gridY: 3 },
      { id: "led", componentSlug: "led-5mm-red", gridX: 16, gridY: 2 },
    ],
    connections: [
      { id: "pi-gpio17-resistor", from: { placementId: "pi", pinKey: "P11" }, to: { placementId: "resistor", pinKey: "A" }, color: "#22c55e", label: "GPIO17" },
      { id: "resistor-led-pi", from: { placementId: "resistor", pinKey: "B" }, to: { placementId: "led", pinKey: "ANODE" }, color: "#ef4444", label: "+" },
      { id: "led-gnd-pi", from: { placementId: "led", pinKey: "CATHODE" }, to: { placementId: "pi", pinKey: "P6" }, color: "#334155", label: "GND" },
    ],
  },
];
