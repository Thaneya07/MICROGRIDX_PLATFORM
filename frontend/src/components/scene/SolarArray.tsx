import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { normalizePower, REFERENCE_MAX_SOLAR_W } from "./sceneUtils";

export interface SolarArrayProps {
  position: [number, number, number];
  generationW: number;
  online: boolean;
  onSelect?: () => void;
}

/** A tilted panel array. Emissive intensity and a subtle pulse track live generation power. */
export function SolarArray({ position, generationW, online, onSelect }: SolarArrayProps) {
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);
  const [hovered, setHovered] = useState(false);
  const intensity = normalizePower(generationW, REFERENCE_MAX_SOLAR_W);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    const pulse = online ? 0.85 + Math.sin(clock.elapsedTime * 2) * 0.15 : 1;
    materialRef.current.emissiveIntensity = online ? intensity * pulse : 0;
  });

  return (
    <group position={position} rotation={[-Math.PI / 6, 0, 0]}>
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
        scale={hovered ? 1.04 : 1}
      >
        <boxGeometry args={[2.4, 0.08, 1.4]} />
        <meshStandardMaterial
          ref={materialRef}
          color={online ? "#1c3a52" : "#2a2f36"}
          emissive="#f5a623"
          emissiveIntensity={0}
          metalness={0.4}
          roughness={0.4}
        />
      </mesh>
      {/* Support post */}
      <mesh position={[0, -0.6, 0]}>
        <cylinderGeometry args={[0.06, 0.06, 1.0, 8]} />
        <meshStandardMaterial color="#38495a" />
      </mesh>
    </group>
  );
}
