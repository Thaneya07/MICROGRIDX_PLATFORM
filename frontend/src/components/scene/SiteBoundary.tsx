export interface SiteBoundaryProps {
  size?: number;
}

/** A low perimeter marking the microgrid site boundary on the ground plane. */
export function SiteBoundary({ size = 6 }: SiteBoundaryProps) {
  const half = size / 2;
  const points: [number, number, number][] = [
    [-half, 0.01, -half],
    [half, 0.01, -half],
    [half, 0.01, half],
    [-half, 0.01, half],
    [-half, 0.01, -half],
  ];
  return (
    <group>
      {points.slice(0, -1).map((p, i) => {
        const next = points[i + 1];
        const midX = (p[0] + next[0]) / 2;
        const midZ = (p[2] + next[2]) / 2;
        const length = Math.hypot(next[0] - p[0], next[2] - p[2]);
        const angle = Math.atan2(next[0] - p[0], next[2] - p[2]);
        return (
          <mesh key={i} position={[midX, 0.02, midZ]} rotation={[0, angle, 0]}>
            <boxGeometry args={[0.04, 0.04, length]} />
            <meshStandardMaterial color="#38495a" emissive="#26313c" emissiveIntensity={0.3} />
          </mesh>
        );
      })}
    </group>
  );
}
