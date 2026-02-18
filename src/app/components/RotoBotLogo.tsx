interface RotoBotLogoProps {
  size?: number;
  className?: string;
}

export function RotoBotLogo({ size = 40, className = "" }: RotoBotLogoProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-[22%] ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Background */}
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(135deg, #01103e 0%, #041d5e 50%, #01103e 100%)",
        }}
      />
      {/* Cyan glow left */}
      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.53,
          height: size * 0.53,
          left: size * 0.01,
          top: size * 0.35,
          background: "rgba(0,184,219,0.3)",
          filter: `blur(${size * 0.17}px)`,
        }}
      />
      {/* Cyan glow right */}
      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.47,
          height: size * 0.47,
          left: size * 0.55,
          top: size * 0.03,
          background: "rgba(0,184,219,0.3)",
          filter: `blur(${size * 0.16}px)`,
        }}
      />
      {/* Logo SVG */}
      <svg
        viewBox="0 0 100 100"
        className="absolute inset-0"
        style={{ width: size, height: size }}
        fill="none"
      >
        {/* Outer eye/lens shape */}
        <ellipse cx="50" cy="50" rx="38" ry="20" stroke="white" strokeWidth="3.5" fill="none" />
        {/* Center robot face */}
        <ellipse cx="50" cy="50" rx="20" ry="20" stroke="white" strokeWidth="3" fill="none" />
        {/* Three vertical bars */}
        <rect x="41" y="42" width="5" height="16" rx="2.5" fill="white" />
        <rect x="47.5" y="42" width="5" height="16" rx="2.5" fill="white" />
        <rect x="54" y="42" width="5" height="16" rx="2.5" fill="white" />
      </svg>
    </div>
  );
}
