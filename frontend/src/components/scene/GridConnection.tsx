import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { normalizePower, REFERENCE_MAX_GRID_W } from "./sceneUtils";

export interface GridConnectionProps {
  position: [number, number, number];
  gridImportW: number;
  gridExportW: number;
  online: boolean;
}

/** Grid connection point / meter. Glows amber on import, teal on export, gray when balanced. */
export function GridConnection({ position, gridImportW, gridExportW, online }: GridConnectionProps) {
  const materialRef = useRef<THREE.MeshStandardMaterial>(null);
  const importing = online && gridImportW > gridExportW && gridImportW > 1;
  const exporting = online && gridExportW > gridImportW && gridExportW > 1;
  const magnitude = normalizePower(Math.max(gridImportW, gridExportW), REFERENCE_MAX_GRID_W);
  const color = importing ? "#f5a623" : exporting ? "#2dd4bf" : "#5a6773";

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    const pulse = importing || exporting ? 0.4 + Math.sin(clock.elapsedTime * 2.5) * 0.2 * magnitude : 0.15;
    materialRef.current.emissiveIntensity = pulse;
  });

  return (
    <group position={position}>
      <mesh position={[0, 0.8, 0]}>
        <cylinderGeometry args={[0.05, 0.05, 1.6, 8]} />
        <meshStandardMaterial color="#38495a" />
      </mesh>
      <mesh position={[0, 1.2, 0]} castShadow>
        <boxGeometry args={[0.35, 0.35, 0.18]} />
        <meshStandardMaterial ref={materialRef} color="#141a21" emissive={color} emissiveIntensity={0.15} />
      </mesh>
    </group>
  );
}
