export interface SensorMarkerProps {
  position: [number, number, number];
  online: boolean;
}

/** Small marker representing a sensor device. Today driven by simulated telemetry; the intended future ESP32/INA219/DHT22 attachment point. */
export function SensorMarker({ position, online }: SensorMarkerProps) {
  return (
    <mesh position={position} castShadow>
      <sphereGeometry args={[0.08, 12, 12]} />
      <meshStandardMaterial
        color={online ? "#8b98a5" : "#38495a"}
        emissive={online ? "#2dd4bf" : "#000000"}
        emissiveIntensity={online ? 0.4 : 0}
      />
    </mesh>
  );
}
