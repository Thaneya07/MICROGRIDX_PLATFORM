import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Line } from "@react-three/drei";

export interface EnergyFlowLineProps {
  from: [number, number, number];
  to: [number, number, number];
  powerW: number;
  referenceMaxW: number;
  color: string;
}

/** A static line between two nodes plus a small glowing marker that travels along it to indicate active flow direction and relative speed. */
export function EnergyFlowLine({ from, to, powerW, referenceMaxW, color }: EnergyFlowLineProps) {
  const markerRef = useRef<THREE.Mesh>(null);
  const progressRef = useRef(0);

  const active = Math.abs(powerW) > 1;
  const reversed = powerW < 0;
  const speed = active ? 0.15 + 0.5 * Math.min(1, Math.abs(powerW) / referenceMaxW) : 0;

  const start = useMemo(() => new THREE.Vector3(...from), [from]);
  const end = useMemo(() => new THREE.Vector3(...to), [to]);

  useFrame((_, delta) => {
    if (!markerRef.current) return;
    if (!active) {
      markerRef.current.visible = false;
      return;
    }
    markerRef.current.visible = true;
    progressRef.current = (progressRef.current + delta * speed) % 1;
    const t = reversed ? 1 - progressRef.current : progressRef.current;
    markerRef.current.position.lerpVectors(start, end, t);
  });

  return (
    <group>
      <Line
        points={[from, to]}
        color={active ? color : "#26313c"}
        lineWidth={active ? 2 : 1}
        transparent
        opacity={active ? 0.6 : 0.3}
      />
      <mesh ref={markerRef}>
        <sphereGeometry args={[0.06, 8, 8]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1} />
      </mesh>
    </group>
  );
}
