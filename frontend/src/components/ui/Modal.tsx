import { HTMLAttributes, ReactNode, useEffect } from "react";
import "./Modal.css";

export interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Modal({ open, onClose, title, children, className = "", ...props }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="mgx-modal-overlay" role="presentation" onClick={onClose}>
      <div
        className={["mgx-modal", className].filter(Boolean).join(" ")}
        role="dialog"
        aria-modal="true"
        aria-labelledby="mgx-modal-title"
        onClick={(e) => e.stopPropagation()}
        {...props}
      >
        <div className="mgx-modal-header">
          <h2 id="mgx-modal-title" className="mgx-modal-title">
            {title}
          </h2>
          <button className="mgx-modal-close" onClick={onClose} aria-label="Close dialog">
            ×
          </button>
        </div>
        <div className="mgx-modal-body">{children}</div>
      </div>
    </div>
  );
}
