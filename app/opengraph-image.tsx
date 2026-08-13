import { ImageResponse } from "next/og";
import { BRAND_INK, BRAND_NAVY, SITE_NAME, SITE_TAGLINE } from "@/lib/site";

export const alt = SITE_NAME;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: BRAND_NAVY,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center" }}>
          <div
            style={{
              width: 88,
              height: 88,
              background: "#ffffff",
              borderRadius: 20,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: 28,
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                border: "6px solid #0c2340",
                transform: "rotate(45deg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <div
                style={{ width: 12, height: 12, background: "#0c2340" }}
              />
            </div>
          </div>
          <div
            style={{
              fontSize: 52,
              fontWeight: 700,
              color: "#ffffff",
              letterSpacing: -1.2,
            }}
          >
            {SITE_NAME}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              fontSize: 28,
              color: BRAND_INK,
              maxWidth: 920,
              lineHeight: 1.35,
            }}
          >
            {SITE_TAGLINE}
          </div>
          <div
            style={{
              marginTop: 28,
              fontSize: 20,
              color: "#97a0ae",
            }}
          >
            Same ruler for every front office since 2006
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
