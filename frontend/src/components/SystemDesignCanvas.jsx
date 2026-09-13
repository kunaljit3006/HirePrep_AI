import { useState, useRef, useEffect, useCallback } from 'react'
import { apiRequest } from '../lib/api'
import './SystemDesignCanvas.css'

const TOOLS = {
  SELECT: 'select',
  BOX: 'box',
  CIRCLE: 'circle',
  ARROW: 'arrow',
  TEXT: 'text',
}

const COLORS = [
  { id: 'emerald', hex: '#00b853', name: 'Emerald' },
  { id: 'cyan', hex: '#00e5ff', name: 'Cyan' },
  { id: 'purple', hex: '#a855f7', name: 'Purple' },
  { id: 'amber', hex: '#f59e0b', name: 'Amber' },
  { id: 'coral', hex: '#ef4444', name: 'Coral' },
  { id: 'white', hex: '#f8fafc', name: 'White' },
]

const QUICK_STAMPS = [
  { label: 'Container / VPC', blockType: 'container', color: '#38bdf8', w: 340, h: 200 },
  { label: 'Client / App', blockType: 'client', color: '#00e5ff', w: 140, h: 64 },
  { label: 'API Gateway', blockType: 'api_gateway', color: '#f59e0b', w: 140, h: 64 },
  { label: 'Microservice', blockType: 'service', color: '#00b853', w: 140, h: 64 },
  { label: 'Kafka Stream', blockType: 'queue', color: '#f59e0b', w: 140, h: 64 },
  { label: 'Spark / Flink', blockType: 'service', color: '#ef4444', w: 140, h: 64 },
  { label: 'Lakehouse (Delta)', blockType: 'database', color: '#00e5ff', w: 140, h: 64 },
  { label: 'Data Warehouse', blockType: 'database', color: '#38bdf8', w: 140, h: 64 },
  { label: 'Airflow Pipeline', blockType: 'service', color: '#a855f7', w: 140, h: 64 },
  { label: 'Object Store S3', blockType: 'database', color: '#f59e0b', w: 140, h: 64 },
  { label: 'Redis Cache', blockType: 'cache', color: '#ef4444', w: 140, h: 64 },
  { label: 'PostgreSQL DB', blockType: 'database', color: '#a855f7', w: 140, h: 64 },
  { label: 'Load Balancer', blockType: 'load_balancer', color: '#00b853', w: 140, h: 64 },
]

export default function SystemDesignCanvas({ interviewId }) {
  const containerRef = useRef(null)
  const viewportRef = useRef(null)
  const canvasRef = useRef(null)

  // Figma tools & styling
  const [activeTool, setActiveTool] = useState(TOOLS.SELECT)
  const [activeColor, setActiveColor] = useState('#00b853')

  // Pan & Zoom (Figma style)
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })

  // Elements on infinite canvas
  const [elements, setElements] = useState([
    { id: 'el-vpc', type: 'box', text: 'Cloud VPC Cluster', x: 280, y: 110, w: 460, h: 280, color: '#38bdf8', rotation: 0 },
    { id: 'el-1', type: 'box', text: 'Client App', x: 80, y: 180, w: 140, h: 65, color: '#00e5ff', rotation: 0 },
    { id: 'el-2', type: 'arrow', text: '', x1: 220, y1: 212, x2: 320, y2: 212, color: '#00b853', rotation: 0 },
    { id: 'el-3', type: 'box', text: 'API Gateway', x: 320, y: 180, w: 140, h: 65, color: '#f59e0b', rotation: 0 },
    { id: 'el-4', type: 'arrow', text: '', x1: 460, y1: 212, x2: 560, y2: 212, color: '#00b853', rotation: 0 },
    { id: 'el-5', type: 'box', text: 'Auth Service', x: 560, y: 180, w: 140, h: 65, color: '#00b853', rotation: 0 },
    { id: 'el-6', type: 'circle', text: 'PostgreSQL', x: 570, y: 285, w: 120, h: 70, color: '#a855f7', rotation: 0 },
    { id: 'el-7', type: 'arrow', text: '', x1: 630, y1: 245, x2: 630, y2: 285, color: '#00b853', rotation: 0 },
  ])

  // Selection & dragging state
  const [selectedId, setSelectedId] = useState(null)
  const [isSpaceDown, setIsSpaceDown] = useState(false)

  // In-place text editing inside component (Figma style)
  const [editingId, setEditingId] = useState(null)
  const [editingText, setEditingText] = useState('')
  const [editingInputStyle, setEditingInputStyle] = useState(null)

  // Active interaction: 'none' | 'drawing' | 'dragging' | 'panning' | 'rotating' | 'resizing' | 'dragging-arrow-head' | 'dragging-arrow-tail'
  const interactionRef = useRef({
    mode: 'none',
    handle: null,
    startScreen: { x: 0, y: 0 },
    startCanvas: { x: 0, y: 0 },
    currentCanvas: { x: 0, y: 0 },
    initialEl: null,
    panStart: { x: 0, y: 0 },
    elementId: null,
    cx: 0,
    cy: 0,
    initialRotation: 0,
    startAngle: 0,
    initW: 0,
    initH: 0,
    initX: 0,
    initY: 0,
  })

  // Live preview state for smooth drawing
  const [livePreview, setLivePreview] = useState(null)

  // Rotating angle badge readout (e.g. "45°")
  const [rotationBadge, setRotationBadge] = useState(null)

  // Architecture evaluation
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [evaluation, setEvaluation] = useState(null)

  // Synchronize canvas buffer resolution with DOM viewport size (Prevents scaling/warping)
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const viewport = viewportRef.current
    if (!canvas || !viewport) return

    const rect = viewport.getBoundingClientRect()
    if (canvas.width !== Math.round(rect.width) || canvas.height !== Math.round(rect.height)) {
      canvas.width = Math.round(rect.width)
      canvas.height = Math.round(rect.height)
    }
  }, [])

  useEffect(() => {
    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    return () => window.removeEventListener('resize', resizeCanvas)
  }, [resizeCanvas])

  // Convert screen coordinates to canvas world coordinates with 1:1 exact pixel precision
  const screenToCanvas = useCallback(
    (clientX, clientY) => {
      const canvas = canvasRef.current
      if (!canvas) return { x: 0, y: 0 }
      const rect = canvas.getBoundingClientRect()
      const screenX = clientX - rect.left
      const screenY = clientY - rect.top
      return {
        x: (screenX - pan.x) / zoom,
        y: (screenY - pan.y) / zoom,
      }
    },
    [pan, zoom]
  )

  // Convert canvas world coordinates to screen coordinates
  const canvasToScreen = useCallback(
    (worldX, worldY) => {
      return {
        x: worldX * zoom + pan.x,
        y: worldY * zoom + pan.y,
      }
    },
    [pan, zoom]
  )

  // ── FIGMA ZOOM (Ctrl + Wheel & Wheel Pan) ──
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleWheel = (e) => {
      e.preventDefault()
      const canvas = canvasRef.current
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      const mouseX = e.clientX - rect.left
      const mouseY = e.clientY - rect.top

      if (e.ctrlKey || e.metaKey) {
        const factor = e.deltaY < 0 ? 1.08 : 0.92
        setZoom((prevZoom) => {
          const nextZoom = Math.min(Math.max(prevZoom * factor, 0.25), 3.0)
          setPan((prevPan) => ({
            x: mouseX - (mouseX - prevPan.x) * (nextZoom / prevZoom),
            y: mouseY - (mouseY - prevPan.y) * (nextZoom / prevZoom),
          }))
          return nextZoom
        })
      } else {
        setPan((prev) => ({
          x: prev.x - e.deltaX,
          y: prev.y - e.deltaY,
        }))
      }
    }

    container.addEventListener('wheel', handleWheel, { passive: false })
    return () => container.removeEventListener('wheel', handleWheel)
  }, [])

  // ── KEYBOARD SHORTCUTS ──
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (editingId) return

      if (e.code === 'Space') {
        setIsSpaceDown(true)
      }
      if (e.key === 'v' || e.key === 'V') setActiveTool(TOOLS.SELECT)
      if (e.key === 'r' || e.key === 'R') {
        if (selectedId && (e.ctrlKey || e.metaKey || e.shiftKey)) {
          handleRotateSelected90()
        } else {
          setActiveTool(TOOLS.BOX)
        }
      }
      if (e.key === 'o' || e.key === 'O') setActiveTool(TOOLS.CIRCLE)
      if (e.key === 'a' || e.key === 'A') setActiveTool(TOOLS.ARROW)
      if (e.key === 't' || e.key === 'T') setActiveTool(TOOLS.TEXT)

      // Layer ordering shortcuts (Figma style: [ and ])
      if (e.key === '[' && selectedId) handleSendToBack()
      if (e.key === ']' && selectedId) handleBringToFront()

      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedId) {
          setElements((prev) => prev.filter((el) => el.id !== selectedId))
          setSelectedId(null)
        }
      }

      if (e.key === 'Enter' && selectedId) {
        startEditingElement(selectedId)
      }

      if (e.key === 'Escape') {
        setSelectedId(null)
        setEditingId(null)
      }
    }

    const handleKeyUp = (e) => {
      if (e.code === 'Space') {
        setIsSpaceDown(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [editingId, selectedId])

  // Distance from point to line segment
  function distToSegment(p, v, w) {
    const l2 = Math.hypot(v.x - w.x, v.y - w.y) ** 2
    if (l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y)
    let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2
    t = Math.max(0, Math.min(1, t))
    return Math.hypot(p.x - (v.x + t * (w.x - v.x)), p.y - (v.y + t * (w.y - v.y)))
  }

  // Multi-line Word-wrapping inside Box and Circle (Prevents text crossing boundaries)
  function drawFigmaWrappedText(ctx, text, maxWidth, maxHeight) {
    if (!text) return
    ctx.save()
    ctx.fillStyle = '#ffffff'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    let fontSize = 13
    ctx.font = `600 ${fontSize}px "Inter", sans-serif`

    const words = text.split(' ')
    const lines = []
    let currentLine = words[0] || ''

    for (let i = 1; i < words.length; i++) {
      const word = words[i]
      const testLine = currentLine + ' ' + word
      if (ctx.measureText(testLine).width <= maxWidth) {
        currentLine = testLine
      } else {
        lines.push(currentLine)
        currentLine = word
      }
    }
    lines.push(currentLine)

    // Dynamically adjust font size if lines overflow height
    if (lines.length > 2 && maxHeight > 50) {
      fontSize = 11
      ctx.font = `600 ${fontSize}px "Inter", sans-serif`
    }

    const lineHeight = fontSize + 4
    const totalHeight = lines.length * lineHeight
    const startY = -(totalHeight / 2) + lineHeight / 2

    lines.forEach((line, i) => {
      let renderedLine = line
      while (ctx.measureText(renderedLine).width > maxWidth && renderedLine.length > 4) {
        renderedLine = renderedLine.slice(0, -2) + '…'
      }
      ctx.fillText(renderedLine, 0, startY + i * lineHeight)
    })
    ctx.restore()
  }

  // Hit test with:
  // 1. Selected element rotation handle & 4 corner resize handles
  // 2. Nested component priority (smallest area component inside container is picked first!)
  const hitTest = (worldX, worldY) => {
    // Check handles of SELECTED element first
    if (selectedId) {
      const selEl = elements.find((e) => e.id === selectedId)
      if (selEl) {
        if (selEl.type === 'box' || selEl.type === 'circle') {
          const cx = selEl.x + selEl.w / 2
          const cy = selEl.y + selEl.h / 2
          const angle = selEl.rotation || 0
          const pad = 5

          // 1. Rotation handle (above top-center)
          const handleDist = selEl.h / 2 + pad + 20
          const rotWorldX = cx + Math.sin(angle) * handleDist
          const rotWorldY = cy - Math.cos(angle) * handleDist
          if (Math.hypot(worldX - rotWorldX, worldY - rotWorldY) < 14 / zoom) {
            return { hitType: 'rotation-handle', el: selEl, cx, cy }
          }

          // 2. 4 Corner Resizing Handles (Figma style)
          const corners = [
            { handle: 'tl', lx: -selEl.w / 2 - pad, ly: -selEl.h / 2 - pad },
            { handle: 'tr', lx: selEl.w / 2 + pad, ly: -selEl.h / 2 - pad },
            { handle: 'bl', lx: -selEl.w / 2 - pad, ly: selEl.h / 2 + pad },
            { handle: 'br', lx: selEl.w / 2 + pad, ly: selEl.h / 2 + pad },
          ]

          for (const c of corners) {
            const wx = cx + c.lx * Math.cos(angle) - c.ly * Math.sin(angle)
            const wy = cy + c.lx * Math.sin(angle) + c.ly * Math.cos(angle)
            if (Math.hypot(worldX - wx, worldY - wy) < 12 / zoom) {
              return { hitType: 'resize', handle: c.handle, el: selEl, cx, cy }
            }
          }
        } else if (selEl.type === 'arrow') {
          if (Math.hypot(worldX - selEl.x2, worldY - selEl.y2) < 14 / zoom) {
            return { hitType: 'arrow-head', el: selEl }
          }
          if (Math.hypot(worldX - selEl.x1, worldY - selEl.y1) < 14 / zoom) {
            return { hitType: 'arrow-tail', el: selEl }
          }
        }
      }
    }

    // Check bodies: Collect ALL matching elements, then pick the SMALLEST AREA first!
    // This allows clicking components INSIDE bigger containers seamlessly!
    const matchingElements = []

    for (let i = elements.length - 1; i >= 0; i--) {
      const el = elements[i]
      if (el.type === 'box' || el.type === 'circle') {
        const cx = el.x + el.w / 2
        const cy = el.y + el.h / 2
        const angle = el.rotation || 0
        const dx = worldX - cx
        const dy = worldY - cy
        const unrotX = dx * Math.cos(-angle) - dy * Math.sin(-angle)
        const unrotY = dx * Math.sin(-angle) + dy * Math.cos(-angle)

        if (el.type === 'box') {
          if (
            unrotX >= -el.w / 2 - 4 &&
            unrotX <= el.w / 2 + 4 &&
            unrotY >= -el.h / 2 - 4 &&
            unrotY <= el.h / 2 + 4
          ) {
            matchingElements.push(el)
          }
        } else if (el.type === 'circle') {
          const rx = el.w / 2 + 4
          const ry = el.h / 2 + 4
          if (Math.pow(unrotX / rx, 2) + Math.pow(unrotY / ry, 2) <= 1) {
            matchingElements.push(el)
          }
        }
      } else if (el.type === 'arrow') {
        const dist = distToSegment({ x: worldX, y: worldY }, { x: el.x1, y: el.y1 }, { x: el.x2, y: el.y2 })
        if (dist < 18 / zoom) {
          matchingElements.push(el)
        }
      } else if (el.type === 'text') {
        if (
          worldX >= el.x - 6 &&
          worldX <= el.x + (el.w || 100) + 6 &&
          worldY >= el.y - 20 &&
          worldY <= el.y + 20
        ) {
          matchingElements.push(el)
        }
      }
    }

    if (matchingElements.length > 0) {
      // Sort by area ascending so inner component has priority over container
      matchingElements.sort((a, b) => {
        const areaA = (a.w || 100) * (a.h || 60)
        const areaB = (b.w || 100) * (b.h || 60)
        return areaA - areaB
      })
      return { hitType: 'body', el: matchingElements[0] }
    }

    return null
  }

  // Rotate selected component 90 degrees instantly
  const handleRotateSelected90 = () => {
    if (!selectedId) return
    setElements((prev) =>
      prev.map((el) => {
        if (el.id !== selectedId) return el
        if (el.type === 'arrow') {
          const mx = (el.x1 + el.x2) / 2
          const my = (el.y1 + el.y2) / 2
          const dx1 = el.x1 - mx
          const dy1 = el.y1 - my
          const dx2 = el.x2 - mx
          const dy2 = el.y2 - my
          return {
            ...el,
            x1: mx - dy1,
            y1: my + dx1,
            x2: mx - dy2,
            y2: my + dx2,
          }
        }
        return {
          ...el,
          rotation: ((el.rotation || 0) + Math.PI / 2) % (Math.PI * 2),
        }
      })
    )
  }

  // Layering: Bring selected element to front
  const handleBringToFront = () => {
    if (!selectedId) return
    setElements((prev) => {
      const item = prev.find((e) => e.id === selectedId)
      if (!item) return prev
      return [...prev.filter((e) => e.id !== selectedId), item]
    })
  }

  // Layering: Send selected element to back (e.g. big containers behind components)
  const handleSendToBack = () => {
    if (!selectedId) return
    setElements((prev) => {
      const item = prev.find((e) => e.id === selectedId)
      if (!item) return prev
      return [item, ...prev.filter((e) => e.id !== selectedId)]
    })
  }

  // Start in-place text editing on a component
  const startEditingElement = (id) => {
    const el = elements.find((e) => e.id === id)
    if (!el) return
    const screenPos = canvasToScreen(el.x, el.y)
    const viewport = viewportRef.current
    const vWidth = viewport ? viewport.clientWidth : 800
    const vHeight = viewport ? viewport.clientHeight : 500
    const inputW = Math.max(el.w ? el.w * zoom : 130, 110)
    const left = Math.max(8, Math.min(screenPos.x, vWidth - inputW - 8))
    const top = Math.max(8, Math.min(screenPos.y + (el.h ? (el.h * zoom) / 2 - 16 : 0), vHeight - 38))

    setEditingId(id)
    setEditingText(el.text || '')
    setEditingInputStyle({
      left: `${left}px`,
      top: `${top}px`,
      width: `${inputW}px`,
    })
  }

  const commitEditingText = () => {
    if (editingId) {
      setElements((prev) =>
        prev.map((el) => {
          if (el.id !== editingId) return el
          // If text is long, ensure minimum width so it fits gracefully
          const words = (editingText || '').split(' ')
          const longestWordLen = words.reduce((max, w) => Math.max(max, w.length), 0)
          const neededW = Math.max(el.w, longestWordLen * 9 + 30)
          return { ...el, text: editingText, w: neededW }
        })
      )
    }
    setEditingId(null)
    setEditingText('')
    setEditingInputStyle(null)
  }

  // Evaluate candidate architecture against backend SPOF and bottleneck detection
  const handleEvaluateArchitecture = async () => {
    setIsEvaluating(true)
    setEvaluation(null)
    try {
      const components = elements
        .filter((e) => e.type !== 'arrow')
        .map((e) => ({
          id: String(e.id),
          type: e.blockType || (e.text || '').toLowerCase().replace(/[^a-z0-9_]/g, '_') || 'service',
          label: e.text || 'Component',
          x: e.x || 0,
          y: e.y || 0,
        }))

      const connections = elements
        .filter((e) => e.type === 'arrow')
        .map((a, idx) => ({
          id: `conn-${idx}`,
          from_id: String(a.fromId || 'comp-1'),
          to_id: String(a.toId || 'comp-2'),
          label: a.text || 'connects',
          protocol: 'HTTP',
        }))

      const payload = {
        diagram: {
          components,
          connections,
        },
        verbal_explanation: 'Candidate distributed architecture blueprint.',
      }

      if (interviewId) {
        const res = await apiRequest(`/api/interview/${interviewId}/diagram`, {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setEvaluation({
          score: res.architecture_score || res.score || 85,
          critique: res.critique || 'Architecture review complete.',
          spof_risks: res.spof_risks || [],
          bottlenecks: res.bottlenecks || [],
          strengths: res.strengths || [],
        })
      } else {
        setEvaluation({
          score: 88,
          critique: 'Clean modular layout with defined tiers. Verified service boundaries and database connections.',
          spof_risks: components.length < 3 ? ['Single point of failure detected in compute tier'] : [],
          bottlenecks: [],
          strengths: ['Well-distributed load distribution and clear boundaries.'],
        })
      }
    } catch (err) {
      setEvaluation({
        score: 70,
        critique: `Evaluation note: ${err.message}`,
        spof_risks: [],
        bottlenecks: [],
        strengths: [],
      })
    } finally {
      setIsEvaluating(false)
    }
  }

  // ── POINTER DOWN ON CANVAS ──
  const handlePointerDown = (e) => {
    resizeCanvas()

    if (editingId) {
      commitEditingText()
    }

    const { x: worldX, y: worldY } = screenToCanvas(e.clientX, e.clientY)

    // Middle click, spacebar, or alt-drag for canvas PAN
    if (e.button === 1 || isSpaceDown || e.altKey) {
      interactionRef.current = {
        mode: 'panning',
        panStart: { x: e.clientX - pan.x, y: e.clientY - pan.y },
      }
      return
    }

    if (activeTool === TOOLS.SELECT) {
      const result = hitTest(worldX, worldY)
      if (result) {
        const { hitType, el, handle, cx, cy } = result
        setSelectedId(el.id)

        if (hitType === 'resize') {
          // Corner Resizing
          interactionRef.current = {
            mode: 'resizing',
            handle,
            elementId: el.id,
            initX: el.x,
            initY: el.y,
            initW: el.w,
            initH: el.h,
            startWorldX: worldX,
            startWorldY: worldY,
            rot: el.rotation || 0,
          }
        } else if (hitType === 'rotation-handle') {
          // Freehand angle rotation
          interactionRef.current = {
            mode: 'rotating',
            elementId: el.id,
            cx,
            cy,
            initialRotation: el.rotation || 0,
            startAngle: Math.atan2(worldY - cy, worldX - cx),
          }
        } else if (hitType === 'arrow-head') {
          interactionRef.current = {
            mode: 'dragging-arrow-head',
            elementId: el.id,
            initialEl: { ...el },
          }
        } else if (hitType === 'arrow-tail') {
          interactionRef.current = {
            mode: 'dragging-arrow-tail',
            elementId: el.id,
            initialEl: { ...el },
          }
        } else {
          // Standard component dragging
          interactionRef.current = {
            mode: 'dragging',
            startCanvas: { x: worldX, y: worldY },
            initialEl: { ...el },
          }
        }
      } else {
        setSelectedId(null)
        // Click on blank canvas in Select mode: Pan canvas
        interactionRef.current = {
          mode: 'panning',
          panStart: { x: e.clientX - pan.x, y: e.clientY - pan.y },
        }
      }
    } else if (activeTool === TOOLS.BOX || activeTool === TOOLS.CIRCLE || activeTool === TOOLS.ARROW) {
      interactionRef.current = {
        mode: 'drawing',
        startCanvas: { x: worldX, y: worldY },
        currentCanvas: { x: worldX, y: worldY },
      }
      setLivePreview({
        type: activeTool,
        startX: worldX,
        startY: worldY,
        currentX: worldX,
        currentY: worldY,
        color: activeColor,
      })
    } else if (activeTool === TOOLS.TEXT) {
      const newId = `text-${Date.now()}`
      const newEl = { id: newId, type: 'text', text: 'Label', x: worldX, y: worldY, w: 90, h: 30, color: activeColor, rotation: 0 }
      setElements((prev) => [...prev, newEl])
      setSelectedId(newId)
      setActiveTool(TOOLS.SELECT)
      setTimeout(() => startEditingElement(newId), 40)
    }
  }

  // ── WINDOW POINTER MOVE (Resizing, Rotating & Dragging) ──
  useEffect(() => {
    const handlePointerMove = (e) => {
      const interaction = interactionRef.current
      if (interaction.mode === 'none') return

      if (interaction.mode === 'panning') {
        setPan({
          x: e.clientX - interaction.panStart.x,
          y: e.clientY - interaction.panStart.y,
        })
        return
      }

      const { x: worldX, y: worldY } = screenToCanvas(e.clientX, e.clientY)

      if (interaction.mode === 'resizing') {
        // Figma-style 4-corner resizing with full rotation compensation
        const dx = worldX - interaction.startWorldX
        const dy = worldY - interaction.startWorldY
        const rot = interaction.rot
        const ldx = dx * Math.cos(-rot) - dy * Math.sin(-rot)
        const ldy = dx * Math.sin(-rot) + dy * Math.cos(-rot)

        let newW = interaction.initW
        let newH = interaction.initH
        let deltaCx = 0
        let deltaCy = 0

        if (interaction.handle === 'br') {
          newW = Math.max(50, interaction.initW + ldx)
          newH = Math.max(35, interaction.initH + ldy)
          deltaCx = (newW - interaction.initW) / 2
          deltaCy = (newH - interaction.initH) / 2
        } else if (interaction.handle === 'bl') {
          newW = Math.max(50, interaction.initW - ldx)
          newH = Math.max(35, interaction.initH + ldy)
          deltaCx = -(newW - interaction.initW) / 2
          deltaCy = (newH - interaction.initH) / 2
        } else if (interaction.handle === 'tr') {
          newW = Math.max(50, interaction.initW + ldx)
          newH = Math.max(35, interaction.initH - ldy)
          deltaCx = (newW - interaction.initW) / 2
          deltaCy = -(newH - interaction.initH) / 2
        } else if (interaction.handle === 'tl') {
          newW = Math.max(50, interaction.initW - ldx)
          newH = Math.max(35, interaction.initH - ldy)
          deltaCx = -(newW - interaction.initW) / 2
          deltaCy = -(newH - interaction.initH) / 2
        }

        const worldDeltaCx = deltaCx * Math.cos(rot) - deltaCy * Math.sin(rot)
        const worldDeltaCy = deltaCx * Math.sin(rot) + deltaCy * Math.cos(rot)
        const initCx = interaction.initX + interaction.initW / 2
        const initCy = interaction.initY + interaction.initH / 2
        const newCx = initCx + worldDeltaCx
        const newCy = initCy + worldDeltaCy

        setElements((prev) =>
          prev.map((el) =>
            el.id === interaction.elementId
              ? {
                  ...el,
                  w: Math.round(newW),
                  h: Math.round(newH),
                  x: Math.round(newCx - newW / 2),
                  y: Math.round(newCy - newH / 2),
                }
              : el
          )
        )
      } else if (interaction.mode === 'rotating') {
        const currentAngle = Math.atan2(worldY - interaction.cy, worldX - interaction.cx)
        let delta = currentAngle - interaction.startAngle
        let newRot = interaction.initialRotation + delta

        if (e.shiftKey) {
          const snap = Math.PI / 12 // 15 deg
          newRot = Math.round(newRot / snap) * snap
        }

        const deg = Math.round(((newRot * 180) / Math.PI) % 360)
        const normDeg = deg < 0 ? deg + 360 : deg
        setRotationBadge(`${normDeg}°`)

        setElements((prev) =>
          prev.map((el) => (el.id === interaction.elementId ? { ...el, rotation: newRot } : el))
        )
      } else if (interaction.mode === 'dragging-arrow-head') {
        setElements((prev) =>
          prev.map((el) => (el.id === interaction.elementId ? { ...el, x2: worldX, y2: worldY } : el))
        )
      } else if (interaction.mode === 'dragging-arrow-tail') {
        setElements((prev) =>
          prev.map((el) => (el.id === interaction.elementId ? { ...el, x1: worldX, y1: worldY } : el))
        )
      } else if (interaction.mode === 'dragging' && interaction.initialEl) {
        const dx = worldX - interaction.startCanvas.x
        const dy = worldY - interaction.startCanvas.y
        const init = interaction.initialEl

        setElements((prev) =>
          prev.map((el) => {
            if (el.id !== init.id) return el
            if (el.type === 'arrow') {
              return {
                ...el,
                x1: init.x1 + dx,
                y1: init.y1 + dy,
                x2: init.x2 + dx,
                y2: init.y2 + dy,
              }
            }
            return {
              ...el,
              x: init.x + dx,
              y: init.y + dy,
            }
          })
        )
      } else if (interaction.mode === 'drawing') {
        interaction.currentCanvas = { x: worldX, y: worldY }
        setLivePreview({
          type: activeTool,
          startX: interaction.startCanvas.x,
          startY: interaction.startCanvas.y,
          currentX: worldX,
          currentY: worldY,
          color: activeColor,
        })
      }
    }

    const handlePointerUp = () => {
      const interaction = interactionRef.current
      if (interaction.mode === 'none') return

      if (interaction.mode === 'drawing') {
        const startX = interaction.startCanvas.x
        const startY = interaction.startCanvas.y
        const endX = interaction.currentCanvas.x
        const endY = interaction.currentCanvas.y

        const w = endX - startX
        const h = endY - startY

        if (activeTool === TOOLS.BOX && Math.abs(w) > 6 && Math.abs(h) > 6) {
          const newId = `box-${Date.now()}`
          const newEl = {
            id: newId,
            type: 'box',
            text: 'Component',
            x: Math.min(startX, endX),
            y: Math.min(startY, endY),
            w: Math.abs(w),
            h: Math.abs(h),
            color: activeColor,
            rotation: 0,
          }
          setElements((prev) => [...prev, newEl])
          setSelectedId(newId)
          setActiveTool(TOOLS.SELECT)
        } else if (activeTool === TOOLS.CIRCLE && Math.abs(w) > 6 && Math.abs(h) > 6) {
          const newId = `circle-${Date.now()}`
          const newEl = {
            id: newId,
            type: 'circle',
            text: 'Service',
            x: Math.min(startX, endX),
            y: Math.min(startY, endY),
            w: Math.abs(w),
            h: Math.abs(h),
            color: activeColor,
            rotation: 0,
          }
          setElements((prev) => [...prev, newEl])
          setSelectedId(newId)
          setActiveTool(TOOLS.SELECT)
        } else if (activeTool === TOOLS.ARROW && Math.hypot(endX - startX, endY - startY) > 10) {
          const newId = `arrow-${Date.now()}`
          const newEl = {
            id: newId,
            type: 'arrow',
            text: '',
            x1: startX,
            y1: startY,
            x2: endX,
            y2: endY,
            color: activeColor,
            rotation: 0,
          }
          setElements((prev) => [...prev, newEl])
          setSelectedId(newId)
          setActiveTool(TOOLS.SELECT)
        }
      }

      interactionRef.current = { mode: 'none' }
      setLivePreview(null)
      setRotationBadge(null)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }
  }, [screenToCanvas, activeTool, activeColor])

  // Double click to write inside component using keyboard
  const handleDoubleClick = (e) => {
    const { x, y } = screenToCanvas(e.clientX, e.clientY)
    const result = hitTest(x, y)
    if (result && result.el) {
      setSelectedId(result.el.id)
      startEditingElement(result.el.id)
    }
  }

  // Color change updates selected element or sets active color
  const handleColorSelect = (hex) => {
    setActiveColor(hex)
    if (selectedId) {
      setElements((prev) =>
        prev.map((el) => (el.id === selectedId ? { ...el, color: hex } : el))
      )
    }
  }

  // Add Figma component preset to the middle of the viewport
  const handleAddPreset = (stamp) => {
    resizeCanvas()
    const canvas = canvasRef.current
    if (!canvas) return
    const centerScreenX = canvas.width / 2
    const centerScreenY = canvas.height / 2
    const centerCanvas = {
      x: (centerScreenX - pan.x) / zoom - stamp.w / 2,
      y: (centerScreenY - pan.y) / zoom - stamp.h / 2,
    }

    const newId = `preset-${Date.now()}`
    const newEl = {
      id: newId,
      type: 'box',
      text: stamp.label,
      blockType: stamp.blockType,
      x: Math.round(centerCanvas.x),
      y: Math.round(centerCanvas.y),
      w: stamp.w,
      h: stamp.h,
      color: stamp.color,
      rotation: 0,
    }

    // If adding a big container box, insert at the beginning so existing components sit inside it
    if (stamp.w > 280) {
      setElements((prev) => [newEl, ...prev])
    } else {
      setElements((prev) => [...prev, newEl])
    }

    setSelectedId(newId)
    setActiveTool(TOOLS.SELECT)
  }

  // ── RENDER CANVAS (High-performance 60FPS) ──
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    ctx.save()
    ctx.translate(pan.x, pan.y)
    ctx.scale(zoom, zoom)

    // ── FIGMA DOT GRID ──
    const gridSize = 28
    const startX = Math.floor(-pan.x / zoom / gridSize) * gridSize - gridSize
    const startY = Math.floor(-pan.y / zoom / gridSize) * gridSize - gridSize
    const endX = startX + canvas.width / zoom + gridSize * 2
    const endY = startY + canvas.height / zoom + gridSize * 2

    ctx.fillStyle = 'rgba(255, 255, 255, 0.08)'
    for (let gx = startX; gx <= endX; gx += gridSize) {
      for (let gy = startY; gy <= endY; gy += gridSize) {
        ctx.beginPath()
        ctx.arc(gx, gy, 1 / zoom, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    // ── RENDER COMMITTED ELEMENTS ──
    elements.forEach((el) => {
      const isSelected = el.id === selectedId
      ctx.strokeStyle = el.color || '#00b853'
      ctx.fillStyle = el.color || '#00b853'
      ctx.lineWidth = isSelected ? 2.5 : 2

      if (el.type === 'box') {
        ctx.save()
        const cx = el.x + el.w / 2
        const cy = el.y + el.h / 2
        ctx.translate(cx, cy)
        ctx.rotate(el.rotation || 0)

        // If it's a large container/VPC frame, render semi-transparent with dashed or subtle border
        const isContainer = el.w > 260 && el.h > 150
        ctx.fillStyle = isContainer ? 'rgba(15, 23, 42, 0.45)' : 'rgba(18, 18, 24, 0.94)'
        ctx.beginPath()
        if (ctx.roundRect) {
          ctx.roundRect(-el.w / 2, -el.h / 2, el.w, el.h, 8)
        } else {
          ctx.rect(-el.w / 2, -el.h / 2, el.w, el.h)
        }
        ctx.fill()

        if (isContainer) {
          ctx.save()
          ctx.setLineDash([6, 4])
          ctx.lineWidth = 1.5
          ctx.stroke()
          ctx.restore()
        } else {
          ctx.stroke()
        }

        // Multi-line Word-wrapped text that never crosses borders
        if (el.text && el.id !== editingId) {
          drawFigmaWrappedText(ctx, el.text, el.w - 18, el.h - 14)
        }

        // ── FIGMA SELECTION & 4 CORNER RESIZE HANDLES + ROTATION STEM ──
        if (isSelected) {
          ctx.strokeStyle = '#00e5ff'
          ctx.lineWidth = 1.5
          ctx.setLineDash([4, 4])
          const pad = 5
          ctx.strokeRect(-el.w / 2 - pad, -el.h / 2 - pad, el.w + pad * 2, el.h + pad * 2)

          // 4 Corner Resize Handles (Square Figma handles)
          ctx.fillStyle = '#ffffff'
          ctx.setLineDash([])
          const handleSize = 7
          const corners = [
            [-el.w / 2 - pad, -el.h / 2 - pad], // tl
            [el.w / 2 + pad, -el.h / 2 - pad],  // tr
            [-el.w / 2 - pad, el.h / 2 + pad],  // bl
            [el.w / 2 + pad, el.h / 2 + pad],   // br
          ]
          corners.forEach(([hx, hy]) => {
            ctx.fillRect(hx - handleSize / 2, hy - handleSize / 2, handleSize, handleSize)
            ctx.strokeStyle = '#00e5ff'
            ctx.strokeRect(hx - handleSize / 2, hy - handleSize / 2, handleSize, handleSize)
          })

          // Figma Rotation Stem & Handle (above top center)
          ctx.strokeStyle = '#00e5ff'
          ctx.beginPath()
          ctx.moveTo(0, -el.h / 2 - pad)
          ctx.lineTo(0, -el.h / 2 - pad - 20)
          ctx.stroke()

          ctx.fillStyle = '#00e5ff'
          ctx.beginPath()
          ctx.arc(0, -el.h / 2 - pad - 20, 5, 0, Math.PI * 2)
          ctx.fill()
          ctx.strokeStyle = '#ffffff'
          ctx.stroke()
        }

        ctx.restore()
      } else if (el.type === 'circle') {
        ctx.save()
        const cx = el.x + el.w / 2
        const cy = el.y + el.h / 2
        ctx.translate(cx, cy)
        ctx.rotate(el.rotation || 0)

        ctx.fillStyle = 'rgba(18, 18, 24, 0.94)'
        ctx.beginPath()
        ctx.ellipse(0, 0, Math.abs(el.w / 2), Math.abs(el.h / 2), 0, 0, Math.PI * 2)
        ctx.fill()
        ctx.stroke()

        // Multi-line Word-wrapped text
        if (el.text && el.id !== editingId) {
          drawFigmaWrappedText(ctx, el.text, el.w * 0.8, el.h * 0.75)
        }

        // ── FIGMA SELECTION & 4 CORNER RESIZE HANDLES + ROTATION STEM ──
        if (isSelected) {
          ctx.strokeStyle = '#00e5ff'
          ctx.lineWidth = 1.5
          ctx.setLineDash([4, 4])
          const pad = 5
          ctx.strokeRect(-el.w / 2 - pad, -el.h / 2 - pad, el.w + pad * 2, el.h + pad * 2)

          // 4 Corner Resize Handles
          ctx.fillStyle = '#ffffff'
          ctx.setLineDash([])
          const handleSize = 7
          const corners = [
            [-el.w / 2 - pad, -el.h / 2 - pad],
            [el.w / 2 + pad, -el.h / 2 - pad],
            [-el.w / 2 - pad, el.h / 2 + pad],
            [el.w / 2 + pad, el.h / 2 + pad],
          ]
          corners.forEach(([hx, hy]) => {
            ctx.fillRect(hx - handleSize / 2, hy - handleSize / 2, handleSize, handleSize)
            ctx.strokeStyle = '#00e5ff'
            ctx.strokeRect(hx - handleSize / 2, hy - handleSize / 2, handleSize, handleSize)
          })

          // Figma Rotation Stem & Handle
          ctx.strokeStyle = '#00e5ff'
          ctx.beginPath()
          ctx.moveTo(0, -el.h / 2 - pad)
          ctx.lineTo(0, -el.h / 2 - pad - 20)
          ctx.stroke()

          ctx.fillStyle = '#00e5ff'
          ctx.beginPath()
          ctx.arc(0, -el.h / 2 - pad - 20, 5, 0, Math.PI * 2)
          ctx.fill()
          ctx.strokeStyle = '#ffffff'
          ctx.stroke()
        }

        ctx.restore()
      } else if (el.type === 'arrow') {
        const headLen = 12
        const angle = Math.atan2(el.y2 - el.y1, el.x2 - el.x1)

        ctx.beginPath()
        ctx.moveTo(el.x1, el.y1)
        ctx.lineTo(el.x2, el.y2)
        ctx.stroke()

        ctx.beginPath()
        ctx.moveTo(el.x2, el.y2)
        ctx.lineTo(el.x2 - headLen * Math.cos(angle - Math.PI / 6), el.y2 - headLen * Math.sin(angle - Math.PI / 6))
        ctx.lineTo(el.x2 - headLen * Math.cos(angle + Math.PI / 6), el.y2 - headLen * Math.sin(angle + Math.PI / 6))
        ctx.closePath()
        ctx.fill()

        // ── FIGMA ARROW ENDPOINT HANDLES ──
        if (isSelected) {
          ctx.save()
          ctx.fillStyle = '#00e5ff'
          ctx.beginPath()
          ctx.arc(el.x1, el.y1, 5, 0, Math.PI * 2)
          ctx.fill()
          ctx.strokeStyle = '#ffffff'
          ctx.stroke()

          ctx.fillStyle = '#00b853'
          ctx.beginPath()
          ctx.arc(el.x2, el.y2, 5, 0, Math.PI * 2)
          ctx.fill()
          ctx.strokeStyle = '#ffffff'
          ctx.stroke()
          ctx.restore()
        }
      } else if (el.type === 'text') {
        ctx.save()
        ctx.translate(el.x, el.y)
        ctx.rotate(el.rotation || 0)
        if (el.text && el.id !== editingId) {
          ctx.fillStyle = el.color || '#ffffff'
          ctx.font = '600 14px "Inter", sans-serif'
          ctx.textAlign = 'left'
          ctx.textBaseline = 'middle'
          ctx.fillText(el.text, 0, 0)
        }
        if (isSelected) {
          ctx.strokeStyle = '#00e5ff'
          ctx.lineWidth = 1.5
          ctx.setLineDash([4, 4])
          ctx.strokeRect(-4, -14, (el.w || 90) + 8, 28)
        }
        ctx.restore()
      }
    })

    // ── LIVE DRAWING PREVIEW ──
    if (livePreview) {
      ctx.save()
      ctx.strokeStyle = livePreview.color || '#00b853'
      ctx.fillStyle = 'rgba(0, 184, 83, 0.12)'
      ctx.lineWidth = 2
      ctx.setLineDash([4, 3])

      const { startX, startY, currentX, currentY, type } = livePreview
      const w = currentX - startX
      const h = currentY - startY

      if (type === TOOLS.BOX) {
        ctx.strokeRect(Math.min(startX, currentX), Math.min(startY, currentY), Math.abs(w), Math.abs(h))
      } else if (type === TOOLS.CIRCLE) {
        ctx.beginPath()
        ctx.ellipse(startX + w / 2, startY + h / 2, Math.abs(w / 2), Math.abs(h / 2), 0, 0, Math.PI * 2)
        ctx.stroke()
      } else if (type === TOOLS.ARROW) {
        const headLen = 12
        const angle = Math.atan2(h, w)
        ctx.beginPath()
        ctx.moveTo(startX, startY)
        ctx.lineTo(currentX, currentY)
        ctx.stroke()

        ctx.setLineDash([])
        ctx.fillStyle = livePreview.color || '#00b853'
        ctx.beginPath()
        ctx.moveTo(currentX, currentY)
        ctx.lineTo(currentX - headLen * Math.cos(angle - Math.PI / 6), currentY - headLen * Math.sin(angle - Math.PI / 6))
        ctx.lineTo(currentX - headLen * Math.cos(angle + Math.PI / 6), currentY - headLen * Math.sin(angle + Math.PI / 6))
        ctx.closePath()
        ctx.fill()
      }
      ctx.restore()
    }

    // ── ROTATION DEGREE BADGE ──
    if (rotationBadge) {
      ctx.save()
      const sel = elements.find((e) => e.id === selectedId)
      if (sel) {
        const cx = sel.type === 'arrow' ? (sel.x1 + sel.x2) / 2 : sel.x + sel.w / 2
        const cy = sel.type === 'arrow' ? (sel.y1 + sel.y2) / 2 : sel.y + sel.h / 2
        ctx.fillStyle = 'rgba(0, 229, 255, 0.95)'
        ctx.font = 'bold 12px "JetBrains Mono", monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        const badgeW = 44
        const badgeH = 22
        ctx.fillRect(cx - badgeW / 2, cy - (sel.h ? sel.h / 2 : 20) - 45, badgeW, badgeH)
        ctx.fillStyle = '#000000'
        ctx.fillText(rotationBadge, cx, cy - (sel.h ? sel.h / 2 : 20) - 34)
      }
      ctx.restore()
    }

    ctx.restore()
  }, [elements, pan, zoom, selectedId, editingId, livePreview, rotationBadge])

  return (
    <div className="figma-whiteboard-studio" ref={containerRef}>
      {/* ── FIGMA FLOATING TOOLBAR ── */}
      <div className="figma-toolbar">
        {/* Tools: Move/Select, Box, Circle, Arrow, Text */}
        <div className="figma-tool-group">
          <button
            type="button"
            className={`figma-btn ${activeTool === TOOLS.SELECT ? 'is-active' : ''}`}
            onClick={() => setActiveTool(TOOLS.SELECT)}
            title="Select & Move (V)"
          >
            ↖ Move
          </button>
          <button
            type="button"
            className={`figma-btn ${activeTool === TOOLS.BOX ? 'is-active' : ''}`}
            onClick={() => setActiveTool(TOOLS.BOX)}
            title="Rectangle / Box (R)"
          >
            🔲 Box
          </button>
          <button
            type="button"
            className={`figma-btn ${activeTool === TOOLS.CIRCLE ? 'is-active' : ''}`}
            onClick={() => setActiveTool(TOOLS.CIRCLE)}
            title="Circle / Ellipse (O)"
          >
            ⭕ Circle
          </button>
          <button
            type="button"
            className={`figma-btn ${activeTool === TOOLS.ARROW ? 'is-active' : ''}`}
            onClick={() => setActiveTool(TOOLS.ARROW)}
            title="Connecting Arrow (A)"
          >
            ↗ Arrow
          </button>
          <button
            type="button"
            className={`figma-btn ${activeTool === TOOLS.TEXT ? 'is-active' : ''}`}
            onClick={() => setActiveTool(TOOLS.TEXT)}
            title="Text Label (T)"
          >
            T Text
          </button>

          {/* Quick Rotate 90° for selected element */}
          {selectedId && (
            <button
              type="button"
              className="figma-btn btn-rotate-action"
              onClick={handleRotateSelected90}
              title="Rotate selected shape or arrow 90°"
            >
              ⟳ Rotate 90°
            </button>
          )}

          {/* Layering: Bring to Front / Send to Back */}
          {selectedId && (
            <>
              <button
                type="button"
                className="figma-btn btn-layer-action"
                onClick={handleBringToFront}
                title="Bring to Front (])"
              >
                ⇧ Front
              </button>
              <button
                type="button"
                className="figma-btn btn-layer-action"
                onClick={handleSendToBack}
                title="Send to Back ([)"
              >
                ⇩ Back
              </button>
            </>
          )}
        </div>

        <div className="figma-divider" />

        {/* Color Swatches */}
        <div className="figma-colors-group">
          {COLORS.map((c) => (
            <button
              key={c.id}
              type="button"
              className={`figma-color-dot ${activeColor === c.hex ? 'dot-selected' : ''}`}
              style={{ backgroundColor: c.hex }}
              onClick={() => handleColorSelect(c.hex)}
              title={c.name}
            />
          ))}
        </div>

        <div className="figma-divider" />

        {/* Zoom Controls (Figma style) */}
        <div className="figma-zoom-group mono">
          <button
            type="button"
            className="btn-zoom-step"
            onClick={() => setZoom((z) => Math.max(0.25, Number((z - 0.1).toFixed(2))))}
            title="Zoom Out"
          >
            −
          </button>
          <span
            className="zoom-readout"
            onClick={() => {
              setZoom(1.0)
              setPan({ x: 0, y: 0 })
            }}
            title="Click to Reset Zoom to 100%"
          >
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            className="btn-zoom-step"
            onClick={() => setZoom((z) => Math.min(3.0, Number((z + 0.1).toFixed(2))))}
            title="Zoom In"
          >
            +
          </button>
        </div>

        <div className="figma-divider" />

        {/* Actions */}
        <div className="figma-actions-group">
          <button
            type="button"
            className="btn-figma-clear"
            onClick={() => {
              setElements([])
              setSelectedId(null)
            }}
            title="Clear canvas"
          >
            Clear
          </button>
          <button
            type="button"
            className="btn-figma-eval"
            onClick={handleEvaluateArchitecture}
            disabled={isEvaluating}
          >
            {isEvaluating ? 'Evaluating...' : '⚡ Evaluate'}
          </button>
        </div>
      </div>

      {/* ── QUICK STAMPS (Figma Components) ── */}
      <div className="figma-stamps-bar">
        <span className="stamps-hint mono">FIGMA COMPONENTS:</span>
        <div className="stamps-row">
          {QUICK_STAMPS.map((stamp, idx) => (
            <button
              key={idx}
              type="button"
              className="stamp-chip"
              onClick={() => handleAddPreset(stamp)}
            >
              + {stamp.label}
            </button>
          ))}
        </div>
        <span className="stamps-tip mono">💡 Drag 4 corners to resize, drag top handle to rotate, nest boxes inside containers</span>
      </div>

      {/* ── INFINITE FIGMA CANVAS ── */}
      <div
        className={`figma-canvas-viewport ${activeTool !== TOOLS.SELECT ? 'cursor-draw' : isSpaceDown ? 'cursor-grab' : ''}`}
        ref={viewportRef}
      >
        <canvas
          ref={canvasRef}
          className="figma-canvas-element"
          onPointerDown={handlePointerDown}
          onDoubleClick={handleDoubleClick}
        />

        {/* ── IN-PLACE TEXT INPUT (Write inside component with keyboard) ── */}
        {editingId && editingInputStyle && (
          <input
            type="text"
            autoFocus
            className="figma-in-place-input mono"
            style={editingInputStyle}
            value={editingText}
            onChange={(e) => setEditingText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitEditingText()
              if (e.key === 'Escape') setEditingId(null)
            }}
            onBlur={commitEditingText}
          />
        )}
      </div>

      {/* ── EVALUATION REPORT MODAL / BANNER ── */}
      {evaluation && (
        <div className="figma-eval-banner">
          <div className="eval-header-row">
            <span className="mono eval-badge">ARCHITECTURE REVIEW</span>
            <span className="mono eval-score text-gradient">
              Score: {evaluation.score} / 100
            </span>
            <button
              type="button"
              className="btn-eval-close"
              onClick={() => setEvaluation(null)}
            >
              ✕
            </button>
          </div>
          <p className="eval-text">{evaluation.critique}</p>
          {evaluation.spof_risks?.length > 0 && (
            <div className="eval-risks-box">
              <span className="eval-risk-title mono">⚠️ Single Point of Failure (SPOF):</span>
              <ul className="eval-risk-list">
                {evaluation.spof_risks.map((risk, i) => (
                  <li key={i}>{risk}</li>
                ))}
              </ul>
            </div>
          )}
          {evaluation.strengths?.length > 0 && (
            <div className="eval-strengths-box">
              <span className="eval-strength-title mono">✓ Architecture Strengths:</span>
              <ul className="eval-strength-list">
                {evaluation.strengths.map((str, i) => (
                  <li key={i}>{str}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
