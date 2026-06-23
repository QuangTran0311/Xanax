import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import dotenv from 'dotenv'
import { buildMcpServer } from './server'

dotenv.config()

async function main() {
  const server = buildMcpServer()
  const transport = new StdioServerTransport()
  await server.connect(transport)
}

main().catch((err) => {
  process.stderr.write(`MCP server error: ${err}\n`)
  process.exit(1)
})
