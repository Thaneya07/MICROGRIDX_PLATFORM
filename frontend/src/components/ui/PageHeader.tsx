import { HTMLAttributes, ReactNode } from "react";
import "./PageHeader.css";

export interface PageHeaderProps extends HTMLAttributes<HTMLDivElement> {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions, className = "", ...props }: PageHeaderProps) {
  return (
    <div className={["mgx-page-header", className].filter(Boolean).join(" ")} {...props}>
      <div>
        {eyebrow && <div className="mgx-page-header-eyebrow">{eyebrow}</div>}
        <h1 className="mgx-page-header-title">{title}</h1>
        {description && <p className="mgx-page-header-description">{description}</p>}
      </div>
      {actions && <div className="mgx-page-header-actions">{actions}</div>}
    </div>
  );
}
