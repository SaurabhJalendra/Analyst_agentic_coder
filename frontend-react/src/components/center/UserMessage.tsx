export function UserMessage({ text }: { text: string }) {
  return (
    <div className="bg-slate-100 rounded-[12px_12px_4px_12px] px-3 py-2 max-w-[75%] ml-auto text-[12px] my-2">
      {text}
    </div>
  );
}
