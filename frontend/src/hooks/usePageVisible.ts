import { useEffect, useState } from "react";

export default function usePageVisible(): boolean {
  const [visible, setVisible] = useState(() => document.visibilityState === "visible");

  useEffect(() => {
    const onVisibilityChange = () => {
      setVisible(document.visibilityState === "visible");
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, []);

  return visible;
}
