
import express from 'express'

export const router = express.Router()

router.post('/webhooks/github', async (req, res) => {
  const event = req.headers['x-github-event']
  console.log('GitHub event received:', event)

  res.status(200).send('Event received')
})
