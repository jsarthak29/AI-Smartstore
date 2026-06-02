export default function ChatPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">AI Assistant</h1>
      <div className="card">
        <p className="text-sm text-slate-600">
          The AI assistant is available everywhere via the floating <b>💬 Ask AI</b> button (bottom-right).
          It can query live store data through tool calls: low stock, expiring products, product details,
          PO history, and can even draft a purchase order for you.
        </p>
        <ul className="mt-3 list-disc list-inside text-sm text-slate-600 space-y-1">
          <li>Which products will run out in the next 7 days?</li>
          <li>Who is the cheapest supplier for rice?</li>
          <li>Show me purchase orders from last month for Bharat FMCG.</li>
          <li>Draft a PO with our lowest-stock dairy items.</li>
        </ul>
      </div>
    </div>
  )
}
