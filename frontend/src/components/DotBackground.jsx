import { useEffect, useRef } from 'react'

export default function DotBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animationId
    let time = 0

    function resize() {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    function draw() {
      time += 0.003
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const spacing = 24
      const cols = Math.ceil(canvas.width / spacing) + 1
      const rows = Math.ceil(canvas.height / spacing) + 1

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = c * spacing
          const y = r * spacing

          /* subtle wave animation on dot opacity */
          const dist = Math.sqrt(
            Math.pow(x - canvas.width / 2, 2) +
            Math.pow(y - canvas.height / 2, 2)
          )
          const wave = Math.sin(dist * 0.003 - time) * 0.5 + 0.5
          const alpha = 0.09 + wave * 0.08

          ctx.beginPath()
          ctx.arc(x, y, 1.35, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`
          ctx.fill()
        }
      }

      animationId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animationId)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        background: '#070707',
      }}
    />
  )
}
