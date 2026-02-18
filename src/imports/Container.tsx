import svgPaths from "./svg-hkyany5zvc";
import imgImageJulian from "figma:asset/5febb12cccc6db13e3a60b3e71b61880d7aee767.png";

function Container2() {
  return <div className="absolute bg-gradient-to-b from-[#030712] h-[872px] left-0 to-[#030712] top-0 via-1/2 via-[#0a0f1d] w-[401px]" data-name="Container" />;
}

function Container3() {
  return <div className="absolute bg-[rgba(43,127,255,0.12)] blur-[80px] left-[220px] rounded-[16777200px] size-[220px] top-[120px]" data-name="Container" />;
}

function Container4() {
  return <div className="absolute bg-[rgba(0,184,219,0.15)] blur-[100px] left-[-50px] rounded-[16777200px] size-[300px] top-[480px]" data-name="Container" />;
}

function Container5() {
  return <div className="absolute h-[872px] left-0 opacity-8 top-0 w-[401px]" data-name="Container" style={{ backgroundImage: "url(\'data:image/svg+xml;utf8,<svg viewBox=\\'0 0 401 872\\' xmlns=\\'http://www.w3.org/2000/svg\\' preserveAspectRatio=\\'none\\'><rect x=\\'0\\' y=\\'0\\' height=\\'100%\\' width=\\'100%\\' fill=\\'url(%23grad)\\' opacity=\\'1\\'/><defs><radialGradient id=\\'grad\\' gradientUnits=\\'userSpaceOnUse\\' cx=\\'0\\' cy=\\'0\\' r=\\'10\\' gradientTransform=\\'matrix(0 -47.989 -47.989 0 200.5 436)\\'><stop stop-color=\\'rgba(255,255,255,1)\\' offset=\\'0.0024938\\'/><stop stop-color=\\'rgba(0,0,0,0)\\' offset=\\'0.0024938\\'/></radialGradient></defs></svg>\')" }} />;
}

function Container1() {
  return (
    <div className="absolute h-[872px] left-0 top-0 w-[401px]" data-name="Container">
      <Container2 />
      <Container3 />
      <Container4 />
      <Container5 />
    </div>
  );
}

function Container6() {
  return <div className="absolute bg-[rgba(255,255,255,0.2)] h-[5px] left-[133.5px] rounded-[16777200px] top-[859px] w-[134px]" data-name="Container" />;
}

function Container10() {
  return <div className="absolute bg-[#3c84ff] blur-[45px] left-0 opacity-40 rounded-[16777200px] size-[110px] top-0" data-name="Container" />;
}

function Container11() {
  return <div className="absolute bg-[#ff7e3c] blur-[25px] left-[16px] opacity-20 rounded-[16777200px] size-[78px] top-[16px]" data-name="Container" />;
}

function Container12() {
  return <div className="absolute bg-[#00f2ff] blur-[60px] left-[-13.75px] opacity-10 rounded-[16777200px] size-[137.5px] top-[-13.75px]" data-name="Container" />;
}

function Icon() {
  return (
    <div className="absolute left-[23px] size-[64px] top-[23px]" data-name="Icon">
      <div className="absolute inset-[-59.37%_-59.37%_-59.38%_-59.38%]">
        <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 140 140">
          <g filter="url(#filter0_d_1_183)" id="Icon">
            <path d={svgPaths.pae1b500} id="Vector" opacity="0.9" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeWidth="6.66667" />
          </g>
          <defs>
            <filter colorInterpolationFilters="sRGB" filterUnits="userSpaceOnUse" height="144" id="filter0_d_1_183" width="144" x="-1.99968" y="-2.00004">
              <feFlood floodOpacity="0" result="BackgroundImageFix" />
              <feColorMatrix in="SourceAlpha" result="hardAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" />
              <feOffset />
              <feGaussianBlur stdDeviation="20" />
              <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.8 0" />
              <feBlend in2="BackgroundImageFix" mode="normal" result="effect1_dropShadow_1_183" />
              <feBlend in="SourceGraphic" in2="effect1_dropShadow_1_183" mode="normal" result="shape" />
            </filter>
          </defs>
        </svg>
      </div>
    </div>
  );
}

function Container9() {
  return (
    <div className="absolute left-[113.5px] size-[110px] top-0" data-name="Container">
      <Container10 />
      <Container11 />
      <Container12 />
      <Icon />
    </div>
  );
}

function Container8() {
  return (
    <div className="absolute h-[110px] left-[32px] top-[140px] w-[337px]" data-name="Container">
      <Container9 />
    </div>
  );
}

function Heading() {
  return (
    <div className="h-[48.398px] relative shrink-0 w-full" data-name="Heading 1">
      <p className="absolute font-['Rubik:Medium',sans-serif] font-medium leading-[48.4px] left-0 text-[44px] text-white top-px tracking-[-0.5148px]">Hi, Julian</p>
    </div>
  );
}

function Paragraph() {
  return (
    <div className="h-[30px] relative shrink-0 w-full" data-name="Paragraph">
      <p className="absolute font-['Rubik:Regular',sans-serif] font-normal leading-[30px] left-0 text-[#9ea1a7] text-[24px] top-0 tracking-[-0.1697px]">Where should we start?</p>
    </div>
  );
}

function Container13() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[6px] h-[84.398px] items-start left-[32px] top-[350px] w-[337px]" data-name="Container">
      <Heading />
      <Paragraph />
    </div>
  );
}

function Text() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[8px] not-italic text-[#0a0a0a] text-[16px] text-center top-[-0.5px] tracking-[-0.3125px]">🍌</p>
      </div>
    </div>
  );
}

function Text1() {
  return (
    <div className="flex-[1_0_0] h-[22.5px] min-h-px min-w-px relative" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Rubik:Medium',sans-serif] font-medium leading-[22.5px] left-[44px] text-[#99a1af] text-[15px] text-center top-[-0.5px] tracking-[-0.6094px]">Create image</p>
      </div>
    </div>
  );
}

function Button() {
  return (
    <div className="bg-[rgba(255,255,255,0.03)] h-[44.5px] relative rounded-[20px] shrink-0 w-[150.703px]" data-name="Button">
      <div aria-hidden="true" className="absolute border border-[rgba(255,255,255,0.05)] border-solid inset-0 pointer-events-none rounded-[20px]" />
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center px-[17px] py-px relative size-full">
        <Text />
        <Text1 />
      </div>
    </div>
  );
}

function Text2() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[8px] not-italic text-[#0a0a0a] text-[16px] text-center top-[-0.5px] tracking-[-0.3125px]">📄</p>
      </div>
    </div>
  );
}

function Text3() {
  return (
    <div className="flex-[1_0_0] h-[22.5px] min-h-px min-w-px relative" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Rubik:Medium',sans-serif] font-medium leading-[22.5px] left-[48px] text-[#99a1af] text-[15px] text-center top-[-0.5px] tracking-[-0.6094px]">Write anything</p>
      </div>
    </div>
  );
}

function Button1() {
  return (
    <div className="bg-[rgba(255,255,255,0.03)] h-[44.5px] relative rounded-[20px] shrink-0 w-[158.57px]" data-name="Button">
      <div aria-hidden="true" className="absolute border border-[rgba(255,255,255,0.05)] border-solid inset-0 pointer-events-none rounded-[20px]" />
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center px-[17px] py-px relative size-full">
        <Text2 />
        <Text3 />
      </div>
    </div>
  );
}

function Text4() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[8px] not-italic text-[#0a0a0a] text-[16px] text-center top-[-0.5px] tracking-[-0.3125px]">📚</p>
      </div>
    </div>
  );
}

function Text5() {
  return (
    <div className="flex-[1_0_0] h-[22.5px] min-h-px min-w-px relative" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Rubik:Medium',sans-serif] font-medium leading-[22.5px] left-[46px] text-[#99a1af] text-[15px] text-center top-[-0.5px] tracking-[-0.6094px]">Help me learn</p>
      </div>
    </div>
  );
}

function Button2() {
  return (
    <div className="bg-[rgba(255,255,255,0.03)] flex-[1_0_0] min-h-px min-w-px relative rounded-[20px] w-[154.023px]" data-name="Button">
      <div aria-hidden="true" className="absolute border border-[rgba(255,255,255,0.05)] border-solid inset-0 pointer-events-none rounded-[20px]" />
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center px-[17px] py-px relative size-full">
        <Text4 />
        <Text5 />
      </div>
    </div>
  );
}

function Container14() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[14px] h-[161.5px] items-start left-[32px] top-[474.4px] w-[337px]" data-name="Container">
      <Button />
      <Button1 />
      <Button2 />
    </div>
  );
}

function StatusBarTime() {
  return (
    <div className="h-[21px] relative rounded-[24px] shrink-0 w-[54px]" data-name="_StatusBar-time">
      <p className="-translate-x-1/2 absolute font-['SF_Pro_Text:Semibold',sans-serif] h-[20px] leading-[21px] left-[27px] not-italic text-[16px] text-center text-white top-px tracking-[-0.32px] w-[54px] whitespace-pre-wrap">9:41</p>
    </div>
  );
}

function LeftSide() {
  return (
    <div className="flex-[1_0_0] h-full min-h-px min-w-px relative" data-name="Left Side">
      <div className="flex flex-col items-center justify-center size-full">
        <div className="content-stretch flex flex-col items-center justify-center pb-[3px] pl-[10px] relative size-full">
          <StatusBarTime />
        </div>
      </div>
    </div>
  );
}

function TrueDepthCamera() {
  return <div className="-translate-x-1/2 -translate-y-1/2 absolute bg-[#020201] h-[37px] left-[calc(50%-22.5px)] rounded-[100px] top-1/2 w-[80px]" data-name="TrueDepth camera" />;
}

function FaceTimeCamera() {
  return <div className="-translate-x-1/2 -translate-y-1/2 absolute bg-[#020201] left-[calc(50%+44px)] rounded-[100px] size-[37px] top-1/2" data-name="FaceTime camera" />;
}

function StatusBarDynamicIsland() {
  return (
    <div className="bg-[#020201] h-[37px] relative rounded-[100px] shrink-0 w-[125px]" data-name="StatusBar-dynamicIsland">
      <TrueDepthCamera />
      <FaceTimeCamera />
    </div>
  );
}

function DynamicIsland() {
  return (
    <div className="content-stretch flex flex-col h-full items-center justify-center relative shrink-0" data-name="Dynamic Island">
      <StatusBarDynamicIsland />
    </div>
  );
}

function SignalWifiBattery() {
  return (
    <div className="h-[13px] relative shrink-0 w-[78.401px]" data-name="Signal, Wifi, Battery">
      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 78.4012 13">
        <g id="Signal, Wifi, Battery">
          <g id="Icon / Mobile Signal">
            <path d={svgPaths.p1ec31400} fill="var(--fill-0, white)" />
            <path d={svgPaths.p19f8d480} fill="var(--fill-0, white)" />
            <path d={svgPaths.p13f4aa00} fill="var(--fill-0, white)" />
            <path d={svgPaths.p1bfb7500} fill="var(--fill-0, white)" />
          </g>
          <path d={svgPaths.p74e6d40} fill="var(--fill-0, white)" id="Wifi" />
          <g id="_StatusBar-battery">
            <path d={svgPaths.pb6b7100} id="Outline" opacity="0.35" stroke="var(--stroke-0, white)" />
            <path d={svgPaths.p9c6aca0} fill="var(--fill-0, white)" id="Battery End" opacity="0.4" />
            <path d={svgPaths.p2cb42c00} fill="var(--fill-0, white)" id="Fill" />
          </g>
        </g>
      </svg>
    </div>
  );
}

function RightSide() {
  return (
    <div className="flex-[1_0_0] h-full min-h-px min-w-px relative" data-name="Right Side">
      <div className="flex flex-row items-center justify-center size-full">
        <div className="content-stretch flex items-center justify-center pr-[11px] relative size-full">
          <SignalWifiBattery />
        </div>
      </div>
    </div>
  );
}

function StatusBar() {
  return (
    <div className="-translate-x-1/2 content-stretch flex h-[59px] items-end justify-center pointer-events-auto sticky top-0 w-[393px]" data-name="Status Bar">
      <LeftSide />
      <DynamicIsland />
      <RightSide />
    </div>
  );
}

function ImageJulian() {
  return (
    <div className="h-[42px] relative rounded-[16777200px] shrink-0 w-full" data-name="Image (Julian)">
      <img alt="" className="absolute inset-0 max-w-none object-cover pointer-events-none rounded-[16777200px] size-full" src={imgImageJulian} />
    </div>
  );
}

function Container15() {
  return (
    <div className="absolute bg-[rgba(255,255,255,0.05)] content-stretch flex flex-col items-start left-[321px] pb-px pt-[3px] px-[3px] rounded-[16777200px] size-[48px] top-[776px]" data-name="Container">
      <div aria-hidden="true" className="absolute border border-[rgba(255,255,255,0.1)] border-solid inset-0 pointer-events-none rounded-[16777200px] shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]" />
      <ImageJulian />
    </div>
  );
}

function Container7() {
  return (
    <div className="absolute h-[872px] left-0 top-0 w-[401px]" data-name="Container">
      <Container8 />
      <Container13 />
      <Container14 />
      <div className="absolute bottom-0 h-[872px] left-[calc(50%+1px)] pointer-events-none top-0">
        <StatusBar />
      </div>
      <Container15 />
    </div>
  );
}

function MenuLine() {
  return <div className="bg-white h-[3.3px] rounded-[15px] shrink-0 w-full" data-name="Menu Line" />;
}

function MenuLine1() {
  return <div className="bg-white h-[3.3px] rounded-[15px] shrink-0 w-[12px]" data-name="Menu Line" />;
}

function MenuLineGroup() {
  return (
    <div className="content-stretch flex flex-col gap-[4.5px] items-end justify-end relative shrink-0 w-[24px]" data-name="Menu Line Group">
      <MenuLine />
      <MenuLine1 />
    </div>
  );
}

function MenuContainer() {
  return (
    <div className="relative size-[36px]" data-name="Menu Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-center justify-center p-[10px] relative size-full">
        <MenuLineGroup />
      </div>
    </div>
  );
}

function Frame3() {
  return <div className="-translate-x-1/2 absolute h-[5.727px] left-[calc(50%+0.01px)] top-[1.91px] w-[4.688px]" />;
}

function Frame2() {
  return (
    <div className="bg-[#009dff] overflow-clip relative rounded-[7px] shrink-0 size-[10px]">
      <Frame3 />
    </div>
  );
}

function Frame4() {
  return (
    <div className="content-stretch flex items-center relative shrink-0">
      <Frame2 />
    </div>
  );
}

function ChevronDown() {
  return (
    <div className="relative shrink-0 size-[15.562px]" data-name="chevron-down">
      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15.562 15.562">
        <g id="chevron-down">
          <path d={svgPaths.p16049880} fill="var(--fill-0, white)" id="Vector" />
        </g>
      </svg>
    </div>
  );
}

function Frame1() {
  return (
    <div className="content-stretch flex gap-[6.225px] items-center relative shrink-0">
      <div className="flex flex-col font-['Poppins:Medium',sans-serif] h-[13px] justify-center leading-[0] not-italic relative shrink-0 text-[13.9px] text-white w-[82px]">
        <p className="leading-[1.2] whitespace-pre-wrap">RotoBot F...</p>
      </div>
      <ChevronDown />
    </div>
  );
}

function Frame5() {
  return (
    <div className="-translate-x-1/2 -translate-y-1/2 absolute content-stretch flex gap-[8px] items-center justify-center left-[calc(50%+0.08px)] top-[calc(50%+0.1px)]">
      <Frame4 />
      <Frame1 />
    </div>
  );
}

function Frame() {
  return (
    <div className="bg-[rgba(255,255,255,0.1)] h-[33.36px] opacity-0 relative rounded-[52.911px] shrink-0 w-[152.9px]">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid overflow-clip relative rounded-[inherit] size-full">
        <Frame5 />
      </div>
    </div>
  );
}

function Icon1() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <div className="absolute inset-[12.5%_20.83%_20.83%_12.5%]" data-name="Vector">
        <div className="absolute inset-[-6.25%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
            <path d={svgPaths.p1ecb7b80} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.99997" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[69.58%_12.5%_12.5%_69.59%]" data-name="Vector">
        <div className="absolute inset-[-23.26%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6.29996 6.29996">
            <path d={svgPaths.p2c83c100} id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.99997" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Button3() {
  return (
    <div className="relative rounded-[21385400px] shrink-0 size-[39.993px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start pt-[7.997px] px-[7.997px] relative size-full">
        <Icon1 />
      </div>
    </div>
  );
}

function Header() {
  return (
    <div className="-translate-x-1/2 absolute content-stretch flex h-[103.985px] items-center justify-between left-[calc(50%-0.56px)] pr-[0.01px] top-[54px] w-[345.873px]" data-name="Header">
      <div className="flex items-center justify-center relative shrink-0">
        <div className="-scale-y-100 flex-none rotate-180">
          <MenuContainer />
        </div>
      </div>
      <Frame />
      <Button3 />
    </div>
  );
}

export default function Container() {
  return (
    <div className="bg-black border border-[#1e2939] border-solid overflow-clip relative rounded-[54px] shadow-[0px_25px_50px_-12px_rgba(0,0,0,0.25)] size-full" data-name="Container">
      <Container1 />
      <Container6 />
      <Container7 />
      <Header />
    </div>
  );
}