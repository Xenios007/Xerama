import type { ButtonHTMLAttributes } from "react";
import "./Button.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
}

export function Button({ variant = "primary", className, ...rest }: ButtonProps) {
  return <button className={`xr-button xr-button--${variant} ${className ?? ""}`.trim()} {...rest} />;
}
