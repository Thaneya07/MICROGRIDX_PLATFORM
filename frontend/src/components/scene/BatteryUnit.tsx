import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { clamp } from "./sceneUtils";

export interface BatteryUnitProps {
  position: [number, number, number];
  socPercent: number | null;
  powerW: number | null; // signed: positive = discharging, negative = charging
  online: boolean;
  onSelect?: () => void;
}

const CHARGE_COLOR = "#2dd4bf";
const DISCHARGE_COLOR = "#f5a623";
const IDLE_COLOR = "#5a6773";

/** Battery enclosure with an internal fill bar scaled to SOC, colored by charge/discharge direction. */
export function BatteryUnit({ position, socPercent, powerW, online, onSelect }: BatteryUnitProps) {
  const fillRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const soc = clamp(socPercent ?? 0, 0, 100);
  const fillHeight = 1.2 * (soc / 100);

  const isCharging = online && powerW !== null && powerW < -1;
  const isDischarging = online && powerW !== null && powerW > 1;
  const fillColor = isCharging ? CHARGE_COLOR : isDischarging ? DISCHARGE_COLOR : IDLE_COLOR;

  useFrame(({ clock }) => {
    if (!fillRef.current) return;
    const active = isCharging || isDischarging;
    const pulse = active ? 1 + Math.sin(clock.elapsedTime * 3) * 0.03 : 1;
    fillRef.current.scale.y = pulse;
  });

  return (
    <group position={position}>
      <mesh
        castShadow
        receiveShadow
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
        scale={hovered ? [1.05, 1.02, 1.05] : [1, 1, 1]}
      >
        <boxGeometry args={[0.7, 1.3, 0.5]} />
        <meshStandardMaterial color="#1a232c" metalness={0.5} roughness={0.5} transparent opacity={0.35} />
      </mesh>
      <mesh ref={fillRef} position={[0, -0.65 + fillHeight / 2, 0]}>
        <boxGeometry args={[0.55, Math.max(0.02, fillHeight), 0.36]} />
        <meshStandardMaterial color={fillColor} emissive={fillColor} emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
}
