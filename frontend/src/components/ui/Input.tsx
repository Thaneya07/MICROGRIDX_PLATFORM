import { forwardRef, InputHTMLAttributes } from "react";
import "./Input.css";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id, className = "", ...props }, ref) => {
    const inputId = id ?? props.name;
    return (
      <div className="mgx-input-group">
        {label && (
          <label className="mgx-input-label" htmlFor={inputId}>
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={["mgx-input", error ? "mgx-input--error" : "", className].filter(Boolean).join(" ")}
          aria-invalid={Boolean(error)}
          {...props}
        />
        {error && <span className="mgx-input-error">{error}</span>}
      </div>
    );
  }
);

Input.displayName = "Input";
