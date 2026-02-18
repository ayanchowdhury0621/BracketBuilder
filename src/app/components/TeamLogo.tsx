import { useState } from "react";
import { useBracket } from "../context/BracketContext";

interface TeamLogoProps {
  teamSlug: string;
  teamShortName?: string;
  teamColor?: string;
  size?: number;
  className?: string;
}

export function TeamLogo({ teamSlug, teamShortName = "", teamColor = "#333", size = 32, className = "" }: TeamLogoProps) {
  const { state } = useBracket();
  const [imgError, setImgError] = useState(false);
  const logoUrl = state.logos[teamSlug];

  if (logoUrl && !imgError) {
    return (
      <img
        src={logoUrl}
        alt={teamShortName}
        onError={() => setImgError(true)}
        className={`object-contain ${className}`}
        style={{ width: size, height: size }}
        loading="lazy"
      />
    );
  }

  return (
    <div
      className={`flex items-center justify-center rounded-lg shrink-0 ${className}`}
      style={{
        width: size,
        height: size,
        background: `${teamColor}33`,
        border: `1px solid ${teamColor}66`,
      }}
    >
      <span style={{ color: "white", fontSize: Math.max(8, size * 0.28), fontWeight: 800, fontFamily: "Rubik, sans-serif" }}>
        {teamShortName.slice(0, 3).toUpperCase()}
      </span>
    </div>
  );
}
