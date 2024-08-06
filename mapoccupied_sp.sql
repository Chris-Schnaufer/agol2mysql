drop function mapoccupied;

DELIMITER //
create function mapoccupied(occ varchar(10))
returns varchar(10) DETERMINISTIC
BEGIN
  declare result varchar(10);
  if strcmp(lower(occ), 'dnc') = 0 or strcmp(lower(occ), 'nf') = 0 or
  strcmp(lower(occ), 'p') = 0 then
    set result = 'Possible';
  elseif strcmp(lower(occ), 'y') = 0 then
	set result = 'Yes';
  elseif occ is null then
    set result = null;
  else
    set result = 'No';
  end if;
  return result;
END//
DELIMITER ;

select mapoccupied(null);
select mapoccupied('DNC');
select mapoccupied('NF');
select mapoccupied('P');
select mapoccupied('Y');
select mapoccupied('N');