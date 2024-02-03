import React, { useState } from "react";

export function Tooltip({ text, children }) {
    const [isVisible, setIsVisible] = useState(false);

    return (
        <div className="relative inline-block"
            id="tooltip-container"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
        >
            {children}
            {isVisible && <div id="tooltip" className="bg-black text-white rounded-md p-2 w-[200px] absolute bottom-full overflow-auto z-10">
                {text}
            </div>}

        </div>
    )

}