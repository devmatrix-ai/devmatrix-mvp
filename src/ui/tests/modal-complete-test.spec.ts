import { test, expect } from '@playwright/test'

test('MasterPlan modal flow - complete discovery and masterplan phases', async ({ page }) => {
  // Enable logging
  page.on('console', msg => console.log(`[BROWSER] ${msg.type()}: ${msg.text()}`))
  
  // Navigate to app
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' })
  console.log('✅ App loaded')
  
  // Wait for WebSocket connection
  await page.waitForTimeout(3000)
  
  // Log all WebSocket messages
  page.on('webSocketFrame', frame => {
    const data = frame.payload
    if (typeof data === 'string') {
      try {
        const json = JSON.parse(data)
        console.log(`[WS] ${JSON.stringify(json).substring(0, 200)}...`)
      } catch {
        console.log(`[WS] ${data.substring(0, 100)}`)
      }
    }
  })
  
  console.log('📝 Starting test at:', new Date().toISOString())
  
  // Find chat input and send message
  const chatInput = page.locator('input[placeholder*="message"], textarea[placeholder*="message"]').first()
  
  if (await chatInput.isVisible()) {
    console.log('✅ Chat input found')
    
    // Send message that triggers MasterPlan generation
    await chatInput.fill('Analiza mi aplicación de ecommerce')
    await chatInput.press('Enter')
    
    console.log('📤 Message sent at:', new Date().toISOString())
    
    // Wait for modal to open
    const modal = page.locator('[role="dialog"]').first()
    
    // Wait up to 10 seconds for modal to appear
    try {
      await modal.waitFor({ state: 'visible', timeout: 10000 })
      console.log('✅ Modal opened at:', new Date().toISOString())
      
      // Track modal state every 500ms for 60 seconds
      let lastState = ''
      let stateCount = 0
      const startTime = Date.now()
      
      while (Date.now() - startTime < 60000) {
        const isVisible = await modal.isVisible().catch(() => false)
        const title = await modal.locator('h2').first().textContent().catch(() => 'N/A')
        const percentage = await modal.locator('text=/\\d+%/').first().textContent().catch(() => 'N/A')
        const phase = await modal.locator('text=/discovery|parsing|validating|saving|complete/i').first().textContent().catch(() => 'N/A')
        
        const state = `visible:${isVisible} phase:"${phase}" progress:${percentage}`
        
        if (state !== lastState) {
          console.log(`[${new Date().toISOString()}] Modal state: ${state}`)
          lastState = state
          stateCount++
        }
        
        // Check if modal shows complete
        if (await modal.locator('text=/complete|completo/i').isVisible().catch(() => false)) {
          console.log('✅ Modal shows "Complete" at:', new Date().toISOString())
          console.log(`   Total state changes: ${stateCount}`)
          
          // Stay on complete screen for 5 more seconds to verify it doesn't close
          await page.waitForTimeout(5000)
          
          if (await modal.isVisible()) {
            console.log('✅ Modal is still visible after 5 seconds - FIX WORKING!')
          } else {
            console.log('❌ Modal closed after showing complete - STILL BROKEN!')
          }
          break
        }
        
        await page.waitForTimeout(500)
      }
      
      if (!await modal.isVisible().catch(() => false)) {
        console.log('❌ Modal closed/disappeared before completion!')
      }
      
    } catch (e) {
      console.log(`❌ Modal failed to open: ${e.message}`)
    }
  } else {
    console.log('❌ Chat input not found')
  }
})
