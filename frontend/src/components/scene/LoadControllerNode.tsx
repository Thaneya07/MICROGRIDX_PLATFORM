import { useState } from "react";
import type { LoadSnapshot } from "@/types/telemetry";

export interface LoadControllerNodeProps {
  position: [number, number, number];
  loads: LoadSnapshot[];
  online: boolean;
  onSelectController?: () => void;
  onSelectLoad?: (load: LoadSnapshot) => void;
}

const STATUS_COLOR: Record<string, string> = {
  ON: "#2dd4bf",
  OFF: "#5a6773",
  UNKNOWN: "#38495a",
};

/** Load controller panel with one small indicator cube per associated load. */
export function LoadControllerNode({ position, loads, online, onSelectController, onSelectLoad }: LoadControllerNodeProps) {
  const [hovered, setHovered] = useState(false);
  return (
    <group position={position}>
      <mesh
        castShadow
        receiveShadow
        onClick={(e) => {
          e.stopPropagation();
          onSelectController?.();
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
        scale={hovered ? 1.08 : 1}
      >
        <boxGeometry args={[0.5, 0.7, 0.15]} />
        <meshStandardMaterial color={online ? "#1c3a52" : "#2a2f36"} metalness={0.3} roughness={0.6} />
      </mesh>
      {loads.map((load, i) => {
        const col = i % 3;
        const row = Math.floor(i / 3);
        const color = online ? STATUS_COLOR[load.status] ?? STATUS_COLOR.UNKNOWN : "#2a2f36";
        return (
          <mesh
            key={load.load_id}
            position={[-0.14 + col * 0.14, 0.2 - row * 0.14, 0.09]}
            onClick={(e) => {
              e.stopPropagation();
              onSelectLoad?.(load);
            }}
            onPointerOver={(e) => {
              e.stopPropagation();
              document.body.style.cursor = "pointer";
            }}
            onPointerOut={() => {
              document.body.style.cursor = "auto";
            }}
          >
            <boxGeometry args={[0.08, 0.08, 0.03]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={load.status === "ON" ? 0.6 : 0.05}
            />
          </mesh>
        );
      })}
    </group>
  );
}
