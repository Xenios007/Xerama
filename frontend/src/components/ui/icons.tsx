import type { SVGProps } from "react";

/** Minimal stroke-icon set matching the Flow-style chrome (Production
 * Studio). Deliberately tiny/dependency-free rather than pulling in an
 * icon library for a dozen glyphs. */

type IconProps = SVGProps<SVGSVGElement>;

function base(props: IconProps) {
  return {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    ...props,
  };
}

export const IconSearch = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.3-4.3" />
  </svg>
);

export const IconFilter = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M4 5h16M7 12h10M10 19h4" />
  </svg>
);

export const IconGrid = (p: IconProps) => (
  <svg {...base(p)}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
);

export const IconPerson = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="12" cy="8" r="3.5" />
    <path d="M4.5 20c1.5-4 4.5-6 7.5-6s6 2 7.5 6" />
  </svg>
);

export const IconFilm = (p: IconProps) => (
  <svg {...base(p)}>
    <rect x="3" y="5" width="18" height="14" rx="1.5" />
    <path d="M3 9h18M8 5v4M16 5v4" />
  </svg>
);

export const IconSparkles = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3z" />
    <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z" />
  </svg>
);

export const IconTrash = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m2 0-.8 12.2a1.5 1.5 0 01-1.5 1.3H7.3a1.5 1.5 0 01-1.5-1.3L5 7h14z" />
  </svg>
);

export const IconCollapse = (p: IconProps) => (
  <svg {...base(p)}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M10 4v16M15 10l-2 2 2 2" />
  </svg>
);

export const IconPlus = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const IconHelp = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9.5a2.5 2.5 0 114 2c-.7.6-1.5 1-1.5 2.2M12 17.5h.01" />
  </svg>
);

export const IconSettings = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 3v2m0 14v2m9-9h-2M5 12H3m14.5-6.5l-1.4 1.4M6.9 17.1l-1.4 1.4m0-13L6.9 6.9m10.2 10.2l1.4 1.4" />
  </svg>
);

export const IconMore = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="12" cy="5" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    <circle cx="12" cy="19" r="1.4" fill="currentColor" stroke="none" />
  </svg>
);

export const IconExpand = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M9 3H3v6M15 3h6v6M3 15v6h6M21 15v6h-6" />
  </svg>
);

export const IconWand = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M4 20L16 8m0 0l3-3m-3 3l3 3M6 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2z" />
  </svg>
);

export const IconSliders = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h13M20 18h0" />
    <circle cx="16" cy="6" r="2" />
    <circle cx="9" cy="12" r="2" />
    <circle cx="16" cy="18" r="2" />
  </svg>
);

export const IconArrowRight = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const IconBack = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M19 12H5M11 6l-6 6 6 6" />
  </svg>
);

export const IconFlower = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="12" cy="8" r="2.4" />
    <circle cx="7" cy="12" r="2.4" />
    <circle cx="17" cy="12" r="2.4" />
    <circle cx="12" cy="16" r="2.4" />
    <path d="M12 18v3" />
  </svg>
);
