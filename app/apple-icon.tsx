import { ImageResponse } from "next/og";
import { BRAND_NAVY } from "@/lib/site";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: BRAND_NAVY,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 92,
            height: 92,
            border: "10px solid #ffffff",
            transform: "rotate(45deg)",
          }}
        >
          <div
            style={{
              width: 28,
              height: 28,
              background: "#ffffff",
            }}
          />
        </div>
      </div>
    ),
    { ...size },
  );
}
