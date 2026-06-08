import { Search } from "lucide-react";
import Select, { components, type DropdownIndicatorProps, type GroupBase, type Props } from "react-select";

export interface SelectOption<T extends string | number = string> {
  value: T;
  label: string;
}

export function SelectField<T extends string | number>(
  props: Props<SelectOption<T>, false, GroupBase<SelectOption<T>>>
) {
  return (
    <Select
      classNamePrefix="sentinel-select"
      components={{ DropdownIndicator: SearchIndicator, ...props.components }}
      noOptionsMessage={() => "Nenhum resultado"}
      loadingMessage={() => "Carregando"}
      placeholder="Selecione"
      {...props}
    />
  );
}

function SearchIndicator<T extends string | number>(
  props: DropdownIndicatorProps<SelectOption<T>, false, GroupBase<SelectOption<T>>>
) {
  return (
    <components.DropdownIndicator {...props}>
      <Search size={16} aria-hidden="true" />
    </components.DropdownIndicator>
  );
}
