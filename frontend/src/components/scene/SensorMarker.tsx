import { useState } from "react";

export interface SensorMarkerProps {
  position: [number, number, number];
  online: boolean;
  onSelect?: () => void;
}

/** Small marker representing a sensor device. Today driven by simulated telemetry; the intended future ESP32/INA219/DHT22 attachment point. */
export function SensorMarker({ position, online, onSelect }: SensorMarkerProps) {
  const [hovered, setHovered] = useState(false);
  return (
    <mesh
      position={position}
      castShadow
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        setHovered(false);
        document.body.style.cursor = "auto";
      }}
      scale={hovered ? 1.5 : 1}
    >
      <sphereGeometry args={[0.08, 12, 12]} />
      <meshStandardMaterial
        color={online ? "#8b98a5" : "#38495a"}
        emissive={online ? "#2dd4bf" : "#000000"}
        emissiveIntensity={online ? 0.4 : 0}
      />
    </mesh>
  );
}
