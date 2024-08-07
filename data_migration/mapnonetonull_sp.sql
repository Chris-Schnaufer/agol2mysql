drop function mapnonetonull;

DELIMITER //
create function mapnonetonull(none_str varchar(10))
returns varchar(10) DETERMINISTIC
BEGIN
  declare result varchar(10);
  if strcmp(lower(none_str), 'none') = 0 then
    set result = null;
  else
    set result = none_str;
  end if;
  return result;
END//
DELIMITER ;

select mapnonetonull('NONE');
select mapnonetonull('ABCD');
select mapnonetonull(null);