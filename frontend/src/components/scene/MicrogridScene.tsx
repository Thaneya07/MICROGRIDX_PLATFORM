import { Canvas } from "@react-three/fiber";
import { Environment, Grid, OrbitControls } from "@react-three/drei";
import type { MicrogridSnapshot } from "@/types/telemetry";
import { SolarArray } from "./SolarArray";
import { BatteryUnit } from "./BatteryUnit";
import { GridConnection } from "./GridConnection";
import { LoadControllerNode } from "./LoadControllerNode";
import { SensorMarker } from "./SensorMarker";
import { EnergyFlowLine } from "./EnergyFlowLine";
import { devicesByType, isDeviceOnline } from "./sceneMapping";
import {
  REFERENCE_MAX_CONSUMPTION_W,
  REFERENCE_MAX_GRID_W,
  REFERENCE_MAX_SOLAR_W,
  REFERENCE_BATTERY_POWER_W,
} from "./sceneUtils";

export interface MicrogridSceneProps {
  snapshot: MicrogridSnapshot;
}

const HUB_POSITION: [number, number, number] = [0, 0.4, 0];
const SOLAR_POSITION: [number, number, number] = [-2.5, 1.6, -1];
const BATTERY_POSITION: [number, number, number] = [1.8, 0.65, 0.5];
const GRID_POSITION: [number, number, number] = [-1.8, 0, 2.2];
const LOAD_CONTROLLER_POSITION: [number, number, number] = [1.8, 0.35, -1.6];

/** Renders the MicrogridX physical energy system as an interactive 3D scene, driven entirely by a MicrogridSnapshot. */
export function MicrogridScene({ snapshot }: MicrogridSceneProps) {
  const reading = snapshot.energy_reading;
  const solarDevice = devicesByType(snapshot, "SOLAR_INVERTER")[0];
  const batteryDevice = devicesByType(snapshot, "BATTERY")[0];
  const meterDevice = devicesByType(snapshot, "METER")[0];
  const loadControllerDevice = devicesByType(snapshot, "LOAD_CONTROLLER")[0];
  const sensorDevices = devicesByType(snapshot, "SENSOR");

  const generationW = reading?.generation_w ?? 0;
  const consumptionW = reading?.consumption_w ?? 0;
  const gridImportW = reading?.grid_import_w ?? 0;
  const gridExportW = reading?.grid_export_w ?? 0;
  const batteryPowerW = reading?.battery_power_w ?? 0;

  return (
    <Canvas shadows camera={{ position: [6, 5, 7], fov: 42 }} dpr={[1, 1.5]}>
      <color attach="background" args={["#0b0f14"]} />
      <fog attach="fog" args={["#0b0f14", 8, 22]} />

      <ambientLight intensity={0.35} />
      <directionalLight position={[5, 8, 4]} intensity={1.1} castShadow shadow-mapSize={[1024, 1024]} />
      <Environment preset="city" />

      <Grid
        position={[0, -0.01, 0]}
        args={[14, 14]}
        cellColor="#26313c"
        sectionColor="#38495a"
        fadeDistance={20}
        fadeStrength={1}
      />

      <SolarArray position={SOLAR_POSITION} generationW={generationW} online={isDeviceOnline(solarDevice)} />
      <BatteryUnit
        position={BATTERY_POSITION}
        socPercent={reading?.battery_soc_percent ?? null}
        powerW={reading?.battery_power_w ?? null}
        online={isDeviceOnline(batteryDevice)}
      />
      <GridConnection
        position={GRID_POSITION}
        gridImportW={gridImportW}
        gridExportW={gridExportW}
        online={isDeviceOnline(meterDevice)}
      />
      <LoadControllerNode
        position={LOAD_CONTROLLER_POSITION}
        loads={snapshot.loads}
        online={isDeviceOnline(loadControllerDevice)}
      />
      {sensorDevices.map((sensor, i) => (
        <SensorMarker key={sensor.device_id} position={[-0.5 + i * 0.4, 0.15, 1.0]} online={isDeviceOnline(sensor)} />
      ))}

      <EnergyFlowLine
        from={SOLAR_POSITION}
        to={HUB_POSITION}
        powerW={generationW}
        referenceMaxW={REFERENCE_MAX_SOLAR_W}
        color="#f5a623"
      />
      <EnergyFlowLine
        from={HUB_POSITION}
        to={LOAD_CONTROLLER_POSITION}
        powerW={consumptionW}
        referenceMaxW={REFERENCE_MAX_CONSUMPTION_W}
        color="#e7ecf2"
      />
      <EnergyFlowLine
        from={BATTERY_POSITION}
        to={HUB_POSITION}
        powerW={batteryPowerW}
        referenceMaxW={REFERENCE_BATTERY_POWER_W}
        color="#2dd4bf"
      />
      <EnergyFlowLine
        from={GRID_POSITION}
        to={HUB_POSITION}
        powerW={gridImportW > 0 ? gridImportW : -gridExportW}
        referenceMaxW={REFERENCE_MAX_GRID_W}
        color="#f5a623"
      />

      <OrbitControls enablePan={false} minDistance={4} maxDistance={14} maxPolarAngle={Math.PI / 2.1} />
    </Canvas>
  );
}
