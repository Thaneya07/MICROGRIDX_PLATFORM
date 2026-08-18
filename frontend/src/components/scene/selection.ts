export interface SelectableDetail {
  label: string;
  value: string;
}

export interface SelectedComponent {
  kind: "solar" | "battery" | "grid" | "loadController" | "sensor" | "load";
  title: string;
  details: SelectableDetail[];
}
