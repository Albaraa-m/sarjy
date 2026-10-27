"use client";

import { animate } from "motion";
import { useEffect, useRef } from "react";

const WHOLE_NUMBER = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const COUNT_DURATION_S = 0.25;

type AnimatedNumberProps = {
  value: number;
};

/** A whole number that counts to its new value when it changes, so the change catches the eye. */
export function AnimatedNumber({ value }: AnimatedNumberProps) {
  const element = useRef<HTMLSpanElement>(null);
  const shown = useRef(value);

  useEffect(() => {
    const counting = animate(shown.current, value, {
      duration: COUNT_DURATION_S,
      ease: "easeOut",
      onUpdate: (latest) => {
        shown.current = latest;
        if (element.current) {
          element.current.textContent = WHOLE_NUMBER.format(latest);
        }
      },
    });
    return () => counting.stop();
  }, [value]);

  return <span ref={element}>{WHOLE_NUMBER.format(value)}</span>;
}
