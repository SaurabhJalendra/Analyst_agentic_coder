// frontend-react/src/components/frame/BrandBar.tsx
export interface BrandBarProps {
  userIdentity?: string;
  userTier?: string;
  rmName?: string;
}

export function BrandBar({ userIdentity, userTier, rmName }: BrandBarProps) {
  return (
    <header className="bg-gradient-to-b from-brand-900 to-brand-800 text-slate-200 px-5 py-3 flex items-center gap-5 text-[11px]">
      <div className="flex items-center gap-2 font-bold tracking-wider text-[14px] text-white">
        <span className="w-5 h-5 rounded bg-gradient-to-br from-gold-500 to-gold-700 text-brand-900 flex items-center justify-center font-black text-[11px]">
          Q
        </span>
        Quant Agent
      </div>
      {(userIdentity || rmName) && (
        <div className="ml-auto text-right text-[10px] leading-tight">
          {userIdentity && (
            <div>
              <strong className="text-white">{userIdentity}</strong>
              {userTier && <> · {userTier}</>}
            </div>
          )}
          {rmName && (
            <div>RM: <span className="text-gold-500 cursor-pointer">{rmName}</span></div>
          )}
        </div>
      )}
    </header>
  );
}
