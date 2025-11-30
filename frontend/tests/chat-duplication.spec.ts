import { test, expect } from '@playwright/test'

test('sending a message only creates one user + one assistant bubble', async ({ page }) => {
  await page.route('**/api/chat', async (route) => {
    const ssePayload = [
      'event: delta\ndata: {"delta":"Hello! I am Syntra."}\n\n',
      'event: done\ndata: {}\n\n',
    ].join('')

    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-store',
        Connection: 'keep-alive',
      },
      body: ssePayload,
    })
  })

  await page.goto('http://localhost:3000/conversations')

  const textarea = page.getByLabel('Message input')
  await textarea.click()
  await textarea.fill('Test duplication')

  const sendButton = page.getByLabel('Send message')
  await sendButton.click()

  // Wait for assistant message to render
  const assistantMessages = page.locator('[role="article"][aria-label="assistant message"]')
  await assistantMessages.first().waitFor()

  const userMessages = page.locator('[role="article"][aria-label="user message"]')
  await expect(userMessages).toHaveCount(1)
  await expect(assistantMessages).toHaveCount(1)
})








