import { useCallback, useEffect, useRef } from "react"

export default function ResizeHandle({ direction = "horizontal", onResize }) {
  const dragging = useRef(false)
  const startPos = useRef(0)

  const onPointerDown = useCallback(
    (event) => {
      dragging.current = true
      startPos.current = direction === "horizontal" ? event.clientX : event.clientY
      event.currentTarget.setPointerCapture(event.pointerId)
      document.body.style.cursor = direction === "horizontal" ? "col-resize" : "row-resize"
      document.body.style.userSelect = "none"
    },
    [direction],
  )

  const onPointerMove = useCallback(
    (event) => {
      if (!dragging.current) return
      const current = direction === "horizontal" ? event.clientX : event.clientY
      onResize(current - startPos.current)
      startPos.current = current
    },
    [direction, onResize],
  )

  const onPointerUp = useCallback((event) => {
    if (!dragging.current) return
    dragging.current = false
    event.currentTarget.releasePointerCapture(event.pointerId)
    document.body.style.cursor = ""
    document.body.style.userSelect = ""
  }, [])

  useEffect(() => {
    return () => {
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    }
  }, [])

  const isHorizontal = direction === "horizontal"

  return (
    <div
      role="separator"
      aria-orientation={isHorizontal ? "vertical" : "horizontal"}
      aria-label="Resize panel"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      className={`group shrink-0 touch-none ${
        isHorizontal
          ? "w-2 cursor-col-resize px-0.5 hover:bg-accent/15 active:bg-accent/25"
          : "h-2 cursor-row-resize py-0.5 hover:bg-accent/15 active:bg-accent/25"
      }`}
    >
      <div
        className={`mx-auto bg-border transition-colors group-hover:bg-accent/70 group-active:bg-accent ${
          isHorizontal ? "h-full w-0.5" : "h-0.5 w-full"
        }`}
      />
    </div>
  )
}
