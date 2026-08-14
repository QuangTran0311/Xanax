import {
  cloneElement,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type FocusEventHandler,
  type KeyboardEventHandler,
  type MouseEventHandler,
  type PointerEventHandler,
  type ReactElement,
} from "react";
import { createPortal } from "react-dom";

type TooltipTargetProps = {
  "aria-describedby"?: string;
  disabled?: boolean;
  onBlur?: FocusEventHandler<HTMLElement>;
  onFocus?: FocusEventHandler<HTMLElement>;
  onKeyDown?: KeyboardEventHandler<HTMLElement>;
  onMouseEnter?: MouseEventHandler<HTMLElement>;
  onMouseLeave?: MouseEventHandler<HTMLElement>;
  onPointerDown?: PointerEventHandler<HTMLElement>;
};

interface TooltipProps {
  label: string;
  children: ReactElement<TooltipTargetProps>;
}

interface TooltipPosition {
  arrowLeft: number;
  left: number;
  placement: "above" | "below";
  top: number;
}

const HOVER_DELAY_MS = 150;
const VIEWPORT_GAP = 8;
const TARGET_GAP = 9;

function supportsHover(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(hover: hover)").matches;
}

function isKeyboardFocused(element: HTMLElement): boolean {
  if (typeof element.matches !== "function") return true;
  try {
    return element.matches(":focus-visible");
  } catch {
    // Older test DOMs may not support :focus-visible; preserve the previous focus behavior there.
    return true;
  }
}

function isTargetVisible(target: HTMLElement, rect: DOMRect): boolean {
  if (!target.isConnected || rect.width <= 0 || rect.height <= 0) return false;

  // Kiểm tra cả chuỗi cha để bắt trường hợp một panel bị ẩn trong lúc tooltip đang mở.
  let element: HTMLElement | null = target;
  while (element) {
    const style = window.getComputedStyle(element);
    if (
      element.hidden
      || element.getAttribute("aria-hidden") === "true"
      || style.display === "none"
      || style.visibility === "hidden"
      || style.visibility === "collapse"
      || style.opacity === "0"
    ) return false;
    element = element.parentElement;
  }
  return true;
}

/**
 * Tooltip dùng chung của Xanax. Nội dung được đưa thẳng lên `document.body` để
 * không bị cắt bởi các vùng cuộn hoặc phần tử có `overflow: hidden`.
 */
export function Tooltip({ label, children }: TooltipProps) {
  const reactId = useId();
  const tooltipId = `tooltip-${reactId.replace(/:/g, "")}`;
  const tooltipRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLSpanElement>(null);
  const targetRef = useRef<HTMLElement | null>(null);
  const hoverTimerRef = useRef<number | null>(null);
  const hoveringRef = useRef(false);
  const focusedRef = useRef(false);
  const dismissedRef = useRef(false);
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState<TooltipPosition | null>(null);

  const clearHoverTimer = () => {
    if (hoverTimerRef.current !== null) {
      window.clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
  };

  const hide = () => {
    clearHoverTimer();
    setVisible(false);
    setPosition(null);
  };

  const show = (target: HTMLElement, delayed: boolean) => {
    if (!label || (delayed && !supportsHover()) || dismissedRef.current) return;
    targetRef.current = target;
    clearHoverTimer();
    if (delayed) {
      hoverTimerRef.current = window.setTimeout(() => {
        hoverTimerRef.current = null;
        setVisible(true);
      }, HOVER_DELAY_MS);
      return;
    }
    setVisible(true);
  };

  const updatePosition = () => {
    const target = targetRef.current;
    const tooltip = tooltipRef.current;
    if (!target || !tooltip) return;

    const targetRect = target.getBoundingClientRect();
    if (!isTargetVisible(target, targetRect)) {
      hide();
      return;
    }
    const tooltipRect = tooltip.getBoundingClientRect();
    if (tooltipRect.width <= 0 || tooltipRect.height <= 0) {
      hide();
      return;
    }
    const placement = targetRect.top >= tooltipRect.height + TARGET_GAP + VIEWPORT_GAP ? "above" : "below";
    const idealLeft = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
    const maxLeft = Math.max(VIEWPORT_GAP, window.innerWidth - tooltipRect.width - VIEWPORT_GAP);
    const left = Math.min(Math.max(idealLeft, VIEWPORT_GAP), maxLeft);
    const rawTop = placement === "above"
      ? targetRect.top - tooltipRect.height - TARGET_GAP
      : targetRect.bottom + TARGET_GAP;
    const maxTop = Math.max(VIEWPORT_GAP, window.innerHeight - tooltipRect.height - VIEWPORT_GAP);
    const top = Math.min(Math.max(rawTop, VIEWPORT_GAP), maxTop);
    const arrowLeft = Math.min(
      Math.max(targetRect.left + targetRect.width / 2 - left, 10),
      Math.max(10, tooltipRect.width - 10),
    );

    setPosition({ arrowLeft, left, placement, top });
  };

  useLayoutEffect(() => {
    if (visible) updatePosition();
  }, [label, visible]);

  useEffect(() => {
    if (!visible) return;
    const reposition = () => updatePosition();
    const trackPointer = (event: PointerEvent) => {
      const target = targetRef.current;
      if (!target?.isConnected) {
        hoveringRef.current = false;
        hide();
        return;
      }

      // Tooltip mở bằng bàn phím phải sống đến blur/Escape; vị trí chuột không được can thiệp.
      // Kiểm tra thêm activeElement vì khi button bị disabled, vài trình duyệt làm mất focus
      // mà không phát blur, nếu chỉ tin ref thì tooltip vẫn có thể bị kẹt.
      if (
        focusedRef.current
        && target.contains(document.activeElement)
        && isKeyboardFocused(target)
      ) return;
      focusedRef.current = false;

      // Dùng toạ độ thay vì event.target để vẫn đúng khi form control disabled đổi hộp hứng hover.
      const rect = target.getBoundingClientRect();
      const pointerInside = event.clientX >= rect.left
        && event.clientX <= rect.right
        && event.clientY >= rect.top
        && event.clientY <= rect.bottom;
      if (!pointerInside) {
        hoveringRef.current = false;
        dismissedRef.current = false;
        hide();
      }
    };
    const target = targetRef.current;
    const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(reposition);
    const intersectionObserver = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.target === target && !entry.isIntersecting)) hide();
      else reposition();
    });
    const visibilityObserver = typeof MutationObserver === "undefined" ? null : new MutationObserver(reposition);

    if (target) {
      resizeObserver?.observe(target);
      intersectionObserver?.observe(target);
      visibilityObserver?.observe(target, {
        attributes: true,
        attributeFilter: ["aria-hidden", "class", "hidden", "style"],
        subtree: true,
      });
      let element: HTMLElement | null = target.parentElement;
      while (element) {
        visibilityObserver?.observe(element, {
          attributes: true,
          attributeFilter: ["aria-hidden", "class", "hidden", "style"],
        });
        element = element.parentElement;
      }
    }
    window.addEventListener("pointermove", trackPointer, { passive: true });
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      resizeObserver?.disconnect();
      intersectionObserver?.disconnect();
      visibilityObserver?.disconnect();
      window.removeEventListener("pointermove", trackPointer);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [visible]);

  useEffect(() => () => {
    clearHoverTimer();
    targetRef.current = null;
  }, []);

  const onMouseEnter: MouseEventHandler<HTMLElement> = () => {
    hoveringRef.current = true;
    dismissedRef.current = false;
    const target = triggerRef.current?.firstElementChild;
    if (target instanceof HTMLElement) show(target, true);
  };
  const onMouseLeave: MouseEventHandler<HTMLElement> = () => {
    hoveringRef.current = false;
    dismissedRef.current = false;
    clearHoverTimer();
    if (!focusedRef.current) hide();
  };
  const onFocus: FocusEventHandler<HTMLElement> = (event) => {
    if (!isKeyboardFocused(event.currentTarget)) return;
    focusedRef.current = true;
    dismissedRef.current = false;
    show(event.currentTarget, false);
  };
  const onBlur: FocusEventHandler<HTMLElement> = () => {
    focusedRef.current = false;
    dismissedRef.current = false;
    if (!hoveringRef.current) hide();
  };
  const onKeyDown: KeyboardEventHandler<HTMLElement> = (event) => {
    if (event.key === "Escape") {
      dismissedRef.current = true;
      hide();
    }
  };
  const onPointerDown: PointerEventHandler<HTMLElement> = () => {
    dismissedRef.current = true;
    focusedRef.current = false;
    hide();
  };

  const describedBy = [children.props["aria-describedby"], tooltipId].filter(Boolean).join(" ");
  const disabled = Boolean(children.props.disabled);
  const target = disabled
    ? cloneElement(children, { "aria-describedby": describedBy })
    : cloneElement(children, {
      "aria-describedby": describedBy,
      onBlur: (event) => { children.props.onBlur?.(event); onBlur(event); },
      onFocus: (event) => { children.props.onFocus?.(event); onFocus(event); },
      onKeyDown: (event) => { children.props.onKeyDown?.(event); onKeyDown(event); },
      onMouseEnter: (event) => { children.props.onMouseEnter?.(event); onMouseEnter(event); },
      onMouseLeave: (event) => { children.props.onMouseLeave?.(event); onMouseLeave(event); },
      onPointerDown: (event) => { children.props.onPointerDown?.(event); onPointerDown(event); },
    });
  const portal = visible && typeof document !== "undefined" ? createPortal(
    <div
      ref={tooltipRef}
      id={tooltipId}
      role="tooltip"
      className={`tooltip-bubble tooltip-bubble--${position?.placement ?? "above"}`}
      style={{
        left: position?.left ?? 0,
        top: position?.top ?? 0,
        visibility: position ? "visible" : "hidden",
      }}
    >
      {label}
      <span className="tooltip-arrow" style={{ left: position?.arrowLeft ?? 0 }} />
    </div>,
    document.body,
  ) : null;

  return <>
    <span
      ref={triggerRef}
      className={`tooltip-trigger${disabled ? " tooltip-trigger--boxed" : ""}`}
      onMouseEnter={disabled ? onMouseEnter : undefined}
      onMouseLeave={disabled ? onMouseLeave : undefined}
      onPointerDown={disabled ? onPointerDown : undefined}
    >
      {target}
    </span>
    {portal}
  </>;
}
