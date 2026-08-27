import AskAgiFooter from '@/beta/components/AskAgiFooter';

export default function SurfaceChrome({ children, askPlaceholder, wide = false }) {
  return (
    <div className={`mx-auto w-full px-4 pb-24 pt-2 sm:px-8 ${wide ? 'max-w-5xl' : 'max-w-3xl lg:max-w-[46rem]'}`}>
      {children}
      <AskAgiFooter placeholder={askPlaceholder} />
    </div>
  );
}
